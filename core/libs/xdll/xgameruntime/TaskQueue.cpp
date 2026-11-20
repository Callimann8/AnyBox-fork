#include "xdll/xgameruntime/xgameruntime.hpp"

#include <chrono>
#include <condition_variable>
#include <deque>
#include <map>
#include <memory>
#include <mutex>
#include <thread>
#include <vector>

namespace {

constexpr std::uint32_t HandleSignature = 0x58545155;

using Clock = std::chrono::steady_clock;

struct Entry {
    void* context;
    XTaskQueueCallback* callback;
};

class Queue;

thread_local const Queue* t_runningQueue = nullptr;

struct Port {
    XTaskQueueDispatchMode mode = XTaskQueueDispatchMode::Manual;
    std::deque<Entry> pending;
    std::size_t inFlight = 0;
    bool draining = false;
};

class Queue : public std::enable_shared_from_this<Queue> {
public:
    Queue(XTaskQueueDispatchMode work, XTaskQueueDispatchMode completion) {
        ports_[0].mode = work;
        ports_[1].mode = completion;
    }

    HRESULT Submit(XTaskQueuePort port, Entry entry) {
        std::unique_lock lock(mutex_);
        if (terminated_) {
            return E_ABORT;
        }
        Port& target = ports_[Index(port)];
        switch (target.mode) {
        case XTaskQueueDispatchMode::Immediate:
            ++target.inFlight;
            lock.unlock();
            Run(entry, false);
            lock.lock();
            --target.inFlight;
            changed_.notify_all();
            return S_OK;
        case XTaskQueueDispatchMode::Manual:
            target.pending.push_back(entry);
            changed_.notify_all();
            return S_OK;
        case XTaskQueueDispatchMode::ThreadPool:
        {
            ++target.inFlight;
            const HRESULT posted = Post([self = shared_from_this(), port, entry] { self->RunPooled(port, entry); });
            if (FAILED(posted)) {
                --target.inFlight;
            }
            return posted;
        }
        case XTaskQueueDispatchMode::SerializedThreadPool:
            target.pending.push_back(entry);
            if (!target.draining) {
                target.draining = true;
                return Post([self = shared_from_this(), port] { self->Drain(port); });
            }
            return S_OK;
        }
        return E_INVALIDARG;
    }

    bool Dispatch(XTaskQueuePort port, std::uint32_t timeoutMs) {
        std::unique_lock lock(mutex_);
        Port& target = ports_[Index(port)];
        if (target.mode != XTaskQueueDispatchMode::Manual) {
            return false;
        }
        const auto ready = [&] { return !target.pending.empty(); };
        if (timeoutMs == XTaskQueueInfinite) {
            changed_.wait(lock, ready);
        } else if (!changed_.wait_for(lock, std::chrono::milliseconds(timeoutMs), ready)) {
            return false;
        }
        const Entry entry = target.pending.front();
        target.pending.pop_front();
        ++target.inFlight;
        lock.unlock();
        Run(entry, false);
        lock.lock();
        --target.inFlight;
        changed_.notify_all();
        return true;
    }

    bool IsEmpty(XTaskQueuePort port) {
        std::lock_guard lock(mutex_);
        const Port& target = ports_[Index(port)];
        return target.pending.empty() && target.inFlight == 0 && !target.draining;
    }

    std::vector<Entry> BeginTerminate() {
        std::lock_guard lock(mutex_);
        terminated_ = true;
        std::vector<Entry> canceled;
        for (Port& port : ports_) {
            canceled.insert(canceled.end(), port.pending.begin(), port.pending.end());
            port.pending.clear();
        }
        return canceled;
    }

    void WaitIdle() {
        std::unique_lock lock(mutex_);
        changed_.wait(lock, [&] {
            for (const Port& port : ports_) {
                if (port.inFlight != 0 || port.draining) {
                    return false;
                }
            }
            return true;
        });
    }

    bool Terminated() {
        std::lock_guard lock(mutex_);
        return terminated_;
    }

    static void Run(const Entry& entry, bool canceled) {
        entry.callback(entry.context, canceled);
    }

private:
    static std::size_t Index(XTaskQueuePort port) { return port == XTaskQueuePort::Work ? 0 : 1; }

    template <typename Work>
    static HRESULT Post(Work work) {
        auto* heap = new Work(std::move(work));
        const auto trampoline = [](PTP_CALLBACK_INSTANCE, void* data) {
            std::unique_ptr<Work> owned(static_cast<Work*>(data));
            (*owned)();
        };
        if (!TrySubmitThreadpoolCallback(trampoline, heap, nullptr)) {
            delete heap;
            return HRESULT_FROM_WIN32(GetLastError());
        }
        return S_OK;
    }

    void RunPooled(XTaskQueuePort port, Entry entry) {
        t_runningQueue = this;
        Run(entry, false);
        t_runningQueue = nullptr;
        std::lock_guard lock(mutex_);
        --ports_[Index(port)].inFlight;
        changed_.notify_all();
    }

    void Drain(XTaskQueuePort port) {
        t_runningQueue = this;
        std::unique_lock lock(mutex_);
        Port& target = ports_[Index(port)];
        while (!target.pending.empty()) {
            const Entry entry = target.pending.front();
            target.pending.pop_front();
            lock.unlock();
            Run(entry, false);
            lock.lock();
        }
        target.draining = false;
        t_runningQueue = nullptr;
        changed_.notify_all();
    }

    std::mutex mutex_;
    std::condition_variable changed_;
    Port ports_[2];
    bool terminated_ = false;
};

struct Delayed {
    std::shared_ptr<Queue> queue;
    XTaskQueuePort port;
    Entry entry;
};

class Scheduler {
public:
    void Add(Clock::time_point due, Delayed item) {
        std::lock_guard lock(mutex_);
        items_.emplace(due, std::move(item));
        if (!started_) {
            started_ = true;
            std::thread([this] { Loop(); }).detach();
        }
        changed_.notify_all();
    }

    std::vector<Entry> Cancel(const Queue* queue) {
        std::lock_guard lock(mutex_);
        std::vector<Entry> canceled;
        for (auto it = items_.begin(); it != items_.end();) {
            if (it->second.queue.get() == queue) {
                canceled.push_back(it->second.entry);
                it = items_.erase(it);
            } else {
                ++it;
            }
        }
        return canceled;
    }

private:
    void Loop() {
        std::unique_lock lock(mutex_);
        for (;;) {
            if (items_.empty()) {
                changed_.wait(lock);
                continue;
            }
            const auto due = items_.begin()->first;
            if (Clock::now() < due) {
                changed_.wait_until(lock, due);
                continue;
            }
            Delayed item = std::move(items_.begin()->second);
            items_.erase(items_.begin());
            lock.unlock();
            if (FAILED(item.queue->Submit(item.port, item.entry))) {
                Queue::Run(item.entry, true);
            }
            lock.lock();
        }
    }

    std::mutex mutex_;
    std::condition_variable changed_;
    std::multimap<Clock::time_point, Delayed> items_;
    bool started_ = false;
};

Scheduler& DelayScheduler() {
    static Scheduler* scheduler = new Scheduler();
    return *scheduler;
}

}

struct XTaskQueueObject {
    std::uint32_t signature = HandleSignature;
    std::shared_ptr<Queue> queue;
};

namespace {

std::mutex g_processMutex;
XTaskQueueHandle g_processQueue = nullptr;
bool g_processQueueSet = false;

XTaskQueueHandle NewHandle(std::shared_ptr<Queue> queue) {
    return new XTaskQueueObject{HandleSignature, std::move(queue)};
}

std::shared_ptr<Queue> Resolve(XTaskQueueHandle handle, const char* function) {
    if (handle == nullptr) {
        XTaskQueueHandle process = nullptr;
        if (!XTaskQueueGetCurrentProcessTaskQueue(&process)) {
            AbxUnsupported(function, "null queue with no process task queue");
        }
        std::shared_ptr<Queue> queue = process->queue;
        XTaskQueueCloseHandle(process);
        return queue;
    }
    if (handle->signature != HandleSignature) {
        AbxUnsupported(function, "handle is not a task queue created by AnyBox");
    }
    return handle->queue;
}

bool ValidMode(XTaskQueueDispatchMode mode) {
    return static_cast<std::uint32_t>(mode) <= static_cast<std::uint32_t>(XTaskQueueDispatchMode::Immediate);
}

bool ValidPort(XTaskQueuePort port) {
    return port == XTaskQueuePort::Work || port == XTaskQueuePort::Completion;
}

}

ABX_API HRESULT XTaskQueueCreate(XTaskQueueDispatchMode workDispatchMode, XTaskQueueDispatchMode completionDispatchMode, XTaskQueueHandle* queue) {
    if (queue == nullptr || !ValidMode(workDispatchMode) || !ValidMode(completionDispatchMode)) {
        return E_INVALIDARG;
    }
    *queue = NewHandle(std::make_shared<Queue>(workDispatchMode, completionDispatchMode));
    return S_OK;
}

ABX_API HRESULT XTaskQueueDuplicateHandle(XTaskQueueHandle queue, XTaskQueueHandle* duplicated) {
    if (queue == nullptr || duplicated == nullptr) {
        return E_INVALIDARG;
    }
    *duplicated = NewHandle(Resolve(queue, __func__));
    return S_OK;
}

ABX_API void XTaskQueueCloseHandle(XTaskQueueHandle queue) {
    if (queue == nullptr) {
        return;
    }
    if (queue->signature != HandleSignature) {
        AbxUnsupported(__func__, "handle is not a task queue created by AnyBox");
    }
    queue->signature = 0;
    delete queue;
}

ABX_API HRESULT XTaskQueueSubmitCallback(XTaskQueueHandle queue, XTaskQueuePort port, void* context, XTaskQueueCallback* callback) {
    if (callback == nullptr || !ValidPort(port)) {
        return E_INVALIDARG;
    }
    return Resolve(queue, __func__)->Submit(port, {context, callback});
}

ABX_API HRESULT XTaskQueueSubmitDelayedCallback(XTaskQueueHandle queue, XTaskQueuePort port, std::uint32_t delayMs, void* context, XTaskQueueCallback* callback) {
    if (callback == nullptr || !ValidPort(port)) {
        return E_INVALIDARG;
    }
    std::shared_ptr<Queue> target = Resolve(queue, __func__);
    if (target->Terminated()) {
        return E_ABORT;
    }
    if (delayMs == 0) {
        return target->Submit(port, {context, callback});
    }
    DelayScheduler().Add(Clock::now() + std::chrono::milliseconds(delayMs), {std::move(target), port, {context, callback}});
    return S_OK;
}

ABX_API bool XTaskQueueDispatch(XTaskQueueHandle queue, XTaskQueuePort port, std::uint32_t timeoutMs) {
    if (!ValidPort(port)) {
        return false;
    }
    return Resolve(queue, __func__)->Dispatch(port, timeoutMs);
}

ABX_API bool XTaskQueueIsEmpty(XTaskQueueHandle queue, XTaskQueuePort port) {
    if (!ValidPort(port)) {
        return true;
    }
    return Resolve(queue, __func__)->IsEmpty(port);
}

ABX_API HRESULT XTaskQueueTerminate(XTaskQueueHandle queue, bool wait, void* context, XTaskQueueTerminatedCallback* callback) {
    std::shared_ptr<Queue> target = Resolve(queue, __func__);
    if (wait && t_runningQueue == target.get()) {
        AbxUnsupported(__func__, "waiting termination from one of the queue's own callbacks");
    }
    std::vector<Entry> canceled = target->BeginTerminate();
    const std::vector<Entry> delayed = DelayScheduler().Cancel(target.get());
    canceled.insert(canceled.end(), delayed.begin(), delayed.end());
    for (const Entry& entry : canceled) {
        Queue::Run(entry, true);
    }
    if (wait) {
        target->WaitIdle();
        if (callback != nullptr) {
            callback(context);
        }
        return S_OK;
    }
    std::thread([target, context, callback] {
        target->WaitIdle();
        if (callback != nullptr) {
            callback(context);
        }
    }).detach();
    return S_OK;
}

ABX_API bool XTaskQueueGetCurrentProcessTaskQueue(XTaskQueueHandle* queue) {
    if (queue == nullptr) {
        return false;
    }
    std::lock_guard lock(g_processMutex);
    if (g_processQueue == nullptr && !g_processQueueSet) {
        g_processQueue = NewHandle(std::make_shared<Queue>(XTaskQueueDispatchMode::ThreadPool, XTaskQueueDispatchMode::ThreadPool));
    }
    if (g_processQueue == nullptr) {
        *queue = nullptr;
        return false;
    }
    *queue = NewHandle(g_processQueue->queue);
    return true;
}

ABX_API void XTaskQueueSetCurrentProcessTaskQueue(XTaskQueueHandle queue) {
    XTaskQueueHandle replacement = queue != nullptr ? NewHandle(Resolve(queue, __func__)) : nullptr;
    std::lock_guard lock(g_processMutex);
    delete g_processQueue;
    g_processQueue = replacement;
    g_processQueueSet = true;
}

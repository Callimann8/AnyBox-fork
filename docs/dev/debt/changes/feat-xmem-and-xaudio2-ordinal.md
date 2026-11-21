# xaudio2

## add Functional

- [XAudio2Create](../../../core/libs/xdll/xaudio2/Ordinals.txt) (xaudio2) - pinned to ordinal 1, the host `xaudio2_9.dll` ordinal, because titles import it by ordinal; the console DLL's ordinal numbering is unverified
  Closes when: the console `xaudio2_9.dll` export table confirms ordinal 1 is `XAudio2Create`

# xmem

## add Functional

- [xmem](../../../core/libs/xdll/xmem/Inventory.cpp) (xmem) - every export stops the title; `XMemAlloc` and `XMemFree` are the GDK's default allocator entry points and the `XALLOC_ATTRIBUTES` layout (alignment, page size, memory type) is not in a public header, so they cannot be implemented for every input yet
  Closes when: the `xmem.h` signatures and `XALLOC_ATTRIBUTES` layout are available from a public header or documentation

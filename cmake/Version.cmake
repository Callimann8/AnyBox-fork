set(ANYBOX_COMMIT "")
set(ANYBOX_MODIFIED "")
find_package(Git QUIET)
if(GIT_FOUND AND EXISTS ${CMAKE_SOURCE_DIR}/.git)
    execute_process(COMMAND ${GIT_EXECUTABLE} rev-parse HEAD
        WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
        OUTPUT_VARIABLE ANYBOX_COMMIT OUTPUT_STRIP_TRAILING_WHITESPACE ERROR_QUIET RESULT_VARIABLE commit_result)
    if(NOT commit_result EQUAL 0)
        set(ANYBOX_COMMIT "")
    endif()
    execute_process(COMMAND ${GIT_EXECUTABLE} status --porcelain --untracked-files=no
        WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
        OUTPUT_VARIABLE status_output OUTPUT_STRIP_TRAILING_WHITESPACE ERROR_QUIET RESULT_VARIABLE status_result)
    if(status_result EQUAL 0 AND NOT ANYBOX_COMMIT STREQUAL "")
        if(status_output STREQUAL "")
            set(ANYBOX_MODIFIED "0")
        else()
            set(ANYBOX_MODIFIED "1")
        endif()
    endif()
endif()
set(ANYBOX_RELEASE "" CACHE STRING "Release tag written into run reports, for example v0.1.0")

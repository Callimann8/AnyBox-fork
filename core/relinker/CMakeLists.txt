add_library(anybox_pe STATIC pe/src/PeImage.cpp)
target_include_directories(anybox_pe PUBLIC pe/include)

add_library(anybox_relinker_core STATIC
    relinker/src/Conversion.cpp
    relinker/src/LibraryMap.cpp
    relinker/src/Registry.cpp)
target_include_directories(anybox_relinker_core PUBLIC relinker/include PRIVATE ${ANYBOX_GENERATED_DIR})
target_link_libraries(anybox_relinker_core PUBLIC anybox_pe)
set_property(SOURCE relinker/src/LibraryMap.cpp APPEND PROPERTY OBJECT_DEPENDS
    ${ANYBOX_GENERATED_DIR}/LibraryMapData.inc ${ANYBOX_GENERATED_DIR}/HostDllsData.inc)

add_executable(relinker main.cpp)
set_target_properties(relinker PROPERTIES OUTPUT_NAME anybox-relinker RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR})
target_link_libraries(relinker PRIVATE anybox_relinker_core)
if(MINGW)
    target_link_options(relinker PRIVATE -static)
endif()

if(BUILD_TESTING)
    add_executable(relinker_tests tests/RelinkerTests.cpp tests/SyntheticPe.cpp)
    target_include_directories(relinker_tests PRIVATE tests)
    target_link_libraries(relinker_tests PRIVATE anybox_relinker_core)
    if(MINGW)
        target_link_options(relinker_tests PRIVATE -static)
    endif()
    foreach(test_case IN ITEMS rename subsystem certificate bound delay unknown host bundled console header-room checksum not-amd64 registry exports)
        add_test(NAME relinker_${test_case} COMMAND relinker_tests ${test_case})
    endforeach()
endif()

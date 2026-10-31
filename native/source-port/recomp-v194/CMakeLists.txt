cmake_minimum_required(VERSION 3.21)
project(bloodborne_native_aot_entry_v194 LANGUAGES C)
set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS OFF)
if(NOT CMAKE_SIZEOF_VOID_P EQUAL 8)
  message(FATAL_ERROR "Native Bloodborne CPU ABI requires a 64-bit host")
endif()
add_executable(native_aot_entry_v194
  native_aot_entry_v194.c
  synthetic_aot_module_v194.c
)
target_include_directories(native_aot_entry_v194 PRIVATE
  "${CMAKE_CURRENT_SOURCE_DIR}"
  "${CMAKE_CURRENT_SOURCE_DIR}/../recomp-v187"
)
if(MSVC)
  target_compile_options(native_aot_entry_v194 PRIVATE /W4 /WX)
else()
  target_compile_options(native_aot_entry_v194 PRIVATE -Wall -Wextra -Werror -pedantic)
endif()
enable_testing()
add_test(NAME native_aot_no_eboot_run_v194 COMMAND native_aot_entry_v194)
add_test(NAME native_aot_refuses_runtime_eboot_argument_v194
  COMMAND native_aot_entry_v194 --eboot forbidden)
set_tests_properties(native_aot_refuses_runtime_eboot_argument_v194
  PROPERTIES WILL_FAIL TRUE)

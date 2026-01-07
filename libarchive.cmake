#
# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

# Find libarchive. Defines the LibArchive::LibArchive target

# Prebuilts are only offered for Windows
if (NOT WIN32)
    add_subdirectory(third_party/libarchive)
    # For consistency with Windows, use the FindLibArchive target name
    add_library(LibArchive::LibArchive ALIAS archive_static)
    return()
endif()

# Try prebuilt
list(APPEND CMAKE_PREFIX_PATH "${PROJECT_SOURCE_DIR}/prebuild/libarchive")
find_package(LibArchive QUIET)
if (LibArchive_FOUND)
    # Requirement specified by archive.h
    target_compile_definitions(LibArchive::LibArchive INTERFACE LIBARCHIVE_STATIC)
    return()
endif()

include(zlib.cmake)

set(BUILD_SHARED_LIBS OFF CACHE INTERNAL "" FORCE)
set(ENABLE_TEST OFF CACHE INTERNAL "" FORCE)
set(ENABLE_OPENSSL OFF CACHE INTERNAL "" FORCE)
set(ENABLE_LIBB2 OFF CACHE INTERNAL "" FORCE)
set(ENABLE_LZ4 OFF CACHE INTERNAL "" FORCE)
set(ENABLE_LZMA OFF CACHE INTERNAL "" FORCE)
set(ENABLE_ZSTD OFF CACHE INTERNAL "" FORCE)
set(ENABLE_BZip2 OFF CACHE INTERNAL "" FORCE)
set(ENABLE_CNG OFF CACHE INTERNAL "" FORCE)
set(ENABLE_TAR OFF CACHE INTERNAL "" FORCE)
set(ENABLE_CPIO OFF CACHE INTERNAL "" FORCE)
set(ENABLE_CAT OFF CACHE INTERNAL "" FORCE)
set(ENABLE_ACL OFF CACHE INTERNAL "" FORCE)
set(ENABLE_INSTALL OFF CACHE INTERNAL "" FORCE)
add_subdirectory(${CMAKE_SOURCE_DIR}/third_party/libarchive)
add_library(LibArchive::LibArchive ALIAS archive_static)

target_compile_definitions(archive_static PUBLIC LIBARCHIVE_STATIC)

# Copyright (c) 2025-present Polymath Robotics, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

include(FetchContent)

find_program(MCAP_BINARY mcap)
if(MCAP_BINARY)
    message(STATUS "mcap binary found at ${MCAP_BINARY}, no need to download")
else()
    message(STATUS "downloading mcap binary for arch ${CMAKE_HOST_SYSTEM_PROCESSOR}...")

    if(${CMAKE_HOST_SYSTEM_PROCESSOR} STREQUAL "x86_64")
        set(MCAP_ARCH "amd64")
    elseif(${CMAKE_HOST_SYSTEM_PROCESSOR} STREQUAL "aarch64")
        set(MCAP_ARCH "arm64")
    else()
        message(FATAL_ERROR "Unknown architecture ${CMAKE_HOST_SYSTEM_PROCESSOR}")
    endif()
    set(binary_name "mcap-linux-${MCAP_ARCH}")

    fetchcontent_declare(
        mcap_binary
        URL https://github.com/foxglove/mcap/releases/download/releases%2Fmcap-cli%2Fv0.0.47/${binary_name}
        DOWNLOAD_NO_EXTRACT true
    )
    fetchcontent_populate(mcap_binary)
    message(STATUS "Successfully downloaded: " ${mcap_binary_SOURCE_DIR})

    install(
        PROGRAMS ${mcap_binary_SOURCE_DIR}/${binary_name}
        DESTINATION bin
        RENAME mcap
        PERMISSIONS OWNER_EXECUTE OWNER_READ OWNER_WRITE
    )
endif()

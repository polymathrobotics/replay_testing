
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

cmake_minimum_required(VERSION 3.14)
project(replay_testing)

# Find dependencies
find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)

include(cmake/install_mcap.cmake)

# Install Python modules and entry points
ament_python_install_package(${PROJECT_NAME})

# Install data files (e.g., test fixtures)
install(DIRECTORY test/fixtures/
  DESTINATION share/${PROJECT_NAME}/test/fixtures
)

install(DIRECTORY test/replay_tests/
  DESTINATION share/${PROJECT_NAME}/test/replay_tests
)

install(PROGRAMS replay_testing/cli.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME replay_test
)

# Expose cmake modules for use by others
install(
  DIRECTORY cmake
  DESTINATION share/${PROJECT_NAME}
)

ament_package(
  CONFIG_EXTRAS "${PROJECT_NAME}-extras.cmake"
)

if(BUILD_TESTING)
  # TODO(troy): Once https://github.com/polymathrobotics/replay_testing/issues/2 is resolved, remove.
  if($ENV{USE_MCAP_PIP})
    find_package(ament_cmake_xmllint REQUIRED)
    ament_xmllint()

    include(cmake/add_replay_test.cmake)

    find_package(ament_cmake_pytest REQUIRED)
    ament_add_pytest_test(pytest ${CMAKE_CURRENT_SOURCE_DIR}/test)

    add_replay_test(test/replay_tests/basic_replay.py)

    if($ENV{USE_NEXUS})
      add_replay_test(test/replay_tests/nexus_replay.py)
    endif()
  endif()
endif()

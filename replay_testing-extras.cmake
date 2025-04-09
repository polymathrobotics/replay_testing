# Copyright (c) 2025-present Polymath Robotics, Inc. All rights reserved
# Proprietary. Any unauthorized copying, distribution, or modification of this software is strictly prohibited.
find_package(ament_cmake_test REQUIRED)
find_package(python_cmake_module REQUIRED)
find_package(PythonExtra REQUIRED)

include("${replay_testing_DIR}/add_replay_test.cmake")

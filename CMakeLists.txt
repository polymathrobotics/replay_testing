cmake_minimum_required(VERSION 3.8)
project(replay_testing)

# Find dependencies
find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
find_package(rclpy REQUIRED)

include(cmake/install_mcap.cmake)
install_mcap()

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

# Define test dependencies
if(BUILD_TESTING)
  include(cmake/add_replay_test.cmake)

  find_package(ament_cmake_pytest REQUIRED)
  ament_add_pytest_test(pytest ${CMAKE_CURRENT_SOURCE_DIR}/test)

  # Dogfood it!
  add_replay_test(test/replay_tests/basic_replay.py)
endif()



# OpenCV Block Measurement System

A comprehensive C++ application for detecting, measuring, and analyzing geometric blocks in images using OpenCV.

## Features

- **Automatic Block Detection**: Detects rectangular/square blocks in images
- **Precise Measurements**: Calculates area, perimeter, dimensions, center, and rotation angle
- **Multiple Display Modes**: Overlay measurements on images or create detailed reports
- **Real-time Camera Support**: Live block detection from webcam
- **Data Export**: Save measurements to CSV format
- **Customizable Parameters**: Adjust detection sensitivity and filtering
- **Test Image Generation**: Built-in test image creation for development

## Installation

### Prerequisites
- OpenCV 4.5.0 or higher
- CMake 3.10 or higher
- C++17 compatible compiler

### Build Instructions
```bash
# Clone or create project directory
mkdir block-measurement-opencv
cd block-measurement-opencv

# Create build directory
mkdir build
cd build

# Configure with CMake
cmake ..

# Build the project
make

# Run the application
./block_measurement
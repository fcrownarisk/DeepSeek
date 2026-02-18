#include "BlockDetector.h"
#include <iostream>
#include <fstream>
#include <cmath>
#include <algorithm>

Block::Block() {
    // Default parameters
    blurKernelSize = 5;
    cannyThresholdLow = 50;
    cannyThresholdHigh = 150;
    morphKernelSize = 3;
    morphIterations = 2;
}

std::vector<Blockmeasure> Block::detectBlocks(const cv::Mat& image, bool drawResults) {
    std::vector<Blockmeasure> measures;
    
    // Check if image is loaded
    if (image.empty()) {
        std::cerr << "Error: Image is empty!" << std::endl;
        return measures;
    }
    
    // Clone original image for drawing
    cv::Mat displayImage = image.clone();
    
    // 1. Preprocess image
    cv::Mat processed = preprocessImage(image);
    
    // 2. Find contours
    std::vector<std::vector<cv::Point>> contours = findContours(processed);
    
    // 3. Calculate measures for each contour
    for (const auto& contour : contours) {
        if (isValidContour(contour)) {
            Blockmeasure measure = calculatemeasures(contour);
            measures.push_back(measure);
            
            // Draw on display image if requested
            if (drawResults) {
                // Draw bounding box
                cv::rectangle(displayImage, measure.boundingBox, 
                            cv::Scalar(0, 255, 0), 2);
                
                // Draw rotated rectangle
                cv::Point2f vertices[4];
                measure.rotatedRect.points(vertices);
                for (int i = 0; i < 4; i++) {
                    cv::line(displayImage, vertices[i], vertices[(i+1)%4], 
                            cv::Scalar(255, 0, 0), 2);
                }
                
                // Draw center point
                cv::circle(displayImage, measure.center, 5, 
                          cv::Scalar(0, 0, 255), -1);
                
                // Draw contour
                cv::drawContours(displayImage, std::vector<std::vector<cv::Point>>{contour}, 
                               0, cv::Scalar(255, 255, 0), 2);
            }
        }
    }
    
    // Show results if requested
    if (drawResults && !measures.empty()) {
        cv::imshow("Detected Blocks", displayImage);
        cv::waitKey(0);
    }
    
    return measures;
}

cv::Mat Block::preprocessImage(const cv::Mat& image) {
    cv::Mat processed;
    
    // 1. Convert to grayscale
    cv::Mat gray;
    if (image.channels() == 3) {
        cv::cvtColor(image, gray, cv::COLOR_BGR2GRAY);
    } else {
        gray = image.clone();
    }
    
    // 2. Apply Gaussian blur to reduce noise
    cv::Mat blurred;
    cv::GaussianBlur(gray, blurred, cv::Size(blurKernelSize, blurKernelSize), 0);
    
    // 3. Apply Canny edge detection
    cv::Mat edges;
    cv::Canny(blurred, edges, cannyThresholdLow, cannyThresholdHigh);
    
    // 4. Apply morphological operations to close gaps
    cv::Mat kernel = cv::getStructuringElement(cv::MORPH_RECT, 
                                               cv::Size(morphKernelSize, morphKernelSize));
    cv::morphologyEx(edges, processed, cv::MORPH_CLOSE, kernel, 
                     cv::Point(-1, -1), morphIterations);
    
    return processed;
}

std::vector<std::vector<cv::Point>> Block::findContours(const cv::Mat& binaryImage) {
    std::vector<std::vector<cv::Point>> contours;
    std::vector<cv::Vec4i> hierarchy;
    
    cv::findContours(binaryImage, contours, hierarchy, 
                     cv::RETR_EXTERNAL, cv::CHAIN_APPROX_SIMPLE);
    
    return contours;
}

Blockmeasure Block::calculatemeasures(const std::vector<cv::Point>& contour) {
    Blockmeasure measure;
    
    // Store contour
    measure.contour = contour;
    
    // Calculate basic measures
    measure.area = cv::contourArea(contour);
    measure.perimeter = cv::arcLength(contour, true);
    
    // Bounding box
    measure.boundingBox = cv::boundingRect(contour);
    
    // Rotated rectangle (minimum area rectangle)
    measure.rotatedRect = cv::minAreaRect(contour);
    measure.angle = measure.rotatedRect.angle;
    
    // Center point
    measure.center = measure.rotatedRect.center;
    
    // Aspect ratio (width/height)
    cv::Size2f size = measure.rotatedRect.size;
    measure.aspectRatio = (size.width > size.height) ? 
                             size.width / size.height : 
                             size.height / size.width;
    
    // Classify block type
    measure.type = classifyBlockType(measure.aspectRatio, measure.area);
    
    return measure;
}

bool Block::isValidContour(const std::vector<cv::Point>& contour, double minArea) {
    double area = cv::contourArea(contour);
    
    // Filter by minimum area
    if (area < minArea) {
        return false;
    }
    
    // Additional filtering can be added here
    // For example: circularity, convexity, etc.
    
    return true;
}

std::string Block::classifyBlockType(double aspectRatio, double area) {
    if (aspectRatio < 1.2) {
        return "Square-like";
    } else if (aspectRatio < 2.0) {
        return "Rectangle";
    } else {
        return "Long Rectangle";
    }
}

std::vector<Blockmeasure> Block::filterBySize(
    const std::vector<Blockmeasure>& blocks, double minArea, double maxArea) {
    
    std::vector<Blockmeasure> filtered;
    
    for (const auto& block : blocks) {
        if (block.area >= minArea && block.area <= maxArea) {
            filtered.push_back(block);
        }
    }
    
    return filtered;
}

Blockmeasure Block::findLargestBlock(const std::vector<Blockmeasure>& blocks) {
    if (blocks.empty()) {
        return Blockmeasure();
    }
    
    auto largest = std::max_element(blocks.begin(), blocks.end(),
        [](const Blockmeasure& a, const Blockmeasure& b) {
            return a.area < b.area;
        });
    
    return *largest;
}

Blockmeasure Block::findSmallestBlock(const std::vector<Blockmeasure>& blocks) {
    if (blocks.empty()) {
        return Blockmeasure();
    }
    
    auto smallest = std::min_element(blocks.begin(), blocks.end(),
        [](const Blockmeasure& a, const Blockmeasure& b) {
            return a.area < b.area;
        });
    
    return *smallest;
}

void Block::savemeasuresToCSV(const std::vector<Blockmeasure>& blocks, 
                                          const std::string& filename) {
    std::ofstream file(filename);
    
    if (!file.is_open()) {
        std::cerr << "Error: Could not open file " << filename << std::endl;
        return;
    }
    
    // Write header
    file << "BlockID,Type,Area,Perimeter,Width,Height,AspectRatio,CenterX,CenterY,Angle\n";
    
    // Write data
    for (size_t i = 0; i < blocks.size(); ++i) {
        const auto& block = blocks[i];
        cv::Size2f size = block.rotatedRect.size;
        
        file << i + 1 << ","
             << block.type << ","
             << block.area << ","
             << block.perimeter << ","
             << size.width << ","
             << size.height << ","
             << block.aspectRatio << ","
             << block.center.x << ","
             << block.center.y << ","
             << block.angle << "\n";
    }
    
    file.close();
    std::cout << "measures saved to " << filename << std::endl;
}

void Block::setPreprocessingParams(int blurSize, int cannyLow, int cannyHigh) {
    blurKernelSize = blurSize;
    cannyThresholdLow = cannyLow;
    cannyThresholdHigh = cannyHigh;
}

void Block::setMorphologyParams(int kernelSize, int iterations) {
    morphKernelSize = kernelSize;
    morphIterations = iterations;
}

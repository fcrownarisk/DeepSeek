#ifndef BLOCKDETECTOR_H
#define BLOCKDETECTOR_H

#include <opencv2/opencv.hpp>
#include <vector>

struct BlockMeasurement {
    cv::Rect boundingBox;
    cv::RotatedRect rotatedRect;
    double area;
    double perimeter;
    cv::Point2f center;
    std::vector<cv::Point> contour;
    double aspectRatio;
    std::string type;
    double angle; // Rotation angle in degrees
};

class BlockDetector {
public:
    BlockDetector();
    
    // Main detection function
    std::vector<BlockMeasurement> detectBlocks(const cv::Mat& image, 
                                               bool drawResults = false);
    
    // Filter blocks by size
    std::vector<BlockMeasurement> filterBySize(const std::vector<BlockMeasurement>& blocks,
                                               double minArea, double maxArea);
    
    // Find largest/smallest block
    BlockMeasurement findLargestBlock(const std::vector<BlockMeasurement>& blocks);
    BlockMeasurement findSmallestBlock(const std::vector<BlockMeasurement>& blocks);
    
    // Save measurements to CSV
    void saveMeasurementsToCSV(const std::vector<BlockMeasurement>& blocks, 
                               const std::string& filename);
    
    // Set detection parameters
    void setPreprocessingParams(int blurSize = 5, int cannyLow = 50, int cannyHigh = 150);
    void setMorphologyParams(int kernelSize = 3, int iterations = 2);
    
private:
    // Image preprocessing
    cv::Mat preprocessImage(const cv::Mat& image);
    
    // Find contours
    std::vector<std::vector<cv::Point>> findContours(const cv::Mat& binaryImage);
    
    // Calculate measurements from contour
    BlockMeasurement calculateMeasurements(const std::vector<cv::Point>& contour);
    
    // Parameters
    int blurKernelSize;
    int cannyThresholdLow;
    int cannyThresholdHigh;
    int morphKernelSize;
    int morphIterations;
    
    // Validate contour (filter noise)
    bool isValidContour(const std::vector<cv::Point>& contour, double minArea = 100.0);
    
    // Classify block type based on shape
    std::string classifyBlockType(double aspectRatio, double area);
};

#endif // BLOCKDETECTOR_H
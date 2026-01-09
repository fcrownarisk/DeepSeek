#ifndef MEASUREMENTDISPLAY_H
#define MEASUREMENTDISPLAY_H

#include <opencv2/opencv.hpp"
#include "BlockDetector.h"

class MeasurementDisplay {
public:
    MeasurementDisplay();
    
    // Display measurements on image
    cv::Mat displayMeasurements(const cv::Mat& image, 
                               const std::vector<BlockMeasurement>& blocks,
                               bool showValues = true);
    
    // Create measurement report image
    cv::Mat createReport(const cv::Mat& image, 
                        const std::vector<BlockMeasurement>& blocks);
    
    // Draw measurement scale/ruler
    void drawScale(cv::Mat& image, double pixelsPerMM, 
                  const cv::Point& start = cv::Point(20, 20));
    
    // Draw grid for reference
    void drawGrid(cv::Mat& image, int gridSize = 50);
    
private:
    // Draw single block with measurements
    void drawBlockWithMeasurements(cv::Mat& image, 
                                  const BlockMeasurement& block, 
                                  int blockID,
                                  bool showValues);
    
    // Add text with background for better visibility
    void putTextWithBackground(cv::Mat& image, const std::string& text,
                              const cv::Point& position, double fontScale = 0.5,
                              const cv::Scalar& textColor = cv::Scalar(255, 255, 255),
                              const cv::Scalar& bgColor = cv::Scalar(0, 0, 0));
    
    // Colors for different block types
    std::map<std::string, cv::Scalar> typeColors;
    
    // Font properties
    int fontFace;
    double fontScale;
    int thickness;
};
#endif // MEASUREMENTDISPLAY_H
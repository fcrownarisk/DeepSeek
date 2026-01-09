
#include "MeasureDisplay.h"
#include <iomanip>
#include <sstream>

MeasureDisplay::MeasureDisplay() {
    // Initialize colors for different block types
    typeColors["Square-like"] = cv::Scalar(0, 255, 0);    // Green
    typeColors["Rectangle"] = cv::Scalar(255, 0, 0);      // Blue
    typeColors["Long Rectangle"] = cv::Scalar(0, 0, 255); // Red
    
    // Font properties
    fontFace = cv::FONT_HERSHEY_SIMPLEX;
    fontScale = 0.5;
    thickness = 2;
}

cv::Mat MeasureDisplay::displayMeasure(const cv::Mat& image, const std::vector<BlockMeasure>& blocks, bool showValues) {
    cv::Mat displayImage = image.clone();
    
    // Draw each block with Measure
    for (size_t i = 0; i < blocks.size(); ++i) {
        drawBlockWithMeasure(displayImage, blocks[i], i + 1, showValues);
    }
    
    // Add summary information
    std::stringstream summary;
    summary << "Blocks Detected: " << blocks.size();
    putTextWithBackground(displayImage, summary.str(), cv::Point(20, 40));
    
    // Calculate total area if needed
    double totalArea = 0;
    for (const auto& block : blocks) {
        totalArea += block.area;
    }
    
    std::stringstream areaText;
    areaText << "Total Area: " << std::fixed << std::setprecision(2) << totalArea << " px²";
    putTextWithBackground(displayImage, areaText.str(), cv::Point(20, 70));
    
    return displayImage;
}

void MeasureDisplay::drawBlockWithMeasure(cv::Mat& image, 
                                                  const BlockMeasure& block,
                                                  int blockID,
                                                  bool showValues) {
    // Get color based on block type
    cv::Scalar color = typeColors[block.type];
    
    // Draw bounding box
    cv::rectangle(image, block.boundingBox, color, 2);
    
    // Draw center point
    cv::circle(image, block.center, 6, color, -1);
    cv::circle(image, block.center, 8, cv::Scalar(255, 255, 255), 2);
    
    // Draw rotated rectangle
    cv::Point2f vertices[4];
    block.rotatedRect.points(vertices);
    for (int i = 0; i < 4; i++) {
        cv::line(image, vertices[i], vertices[(i+1)%4], cv::Scalar(255, 255, 0), 1);
    }
    
    if (showValues) {
        // Create Measure text
        std::stringstream text;
        text << "ID: " << blockID << " | ";
        text << "Area: " << std::fixed << std::setprecision(1) << block.area << "px²";
        
        // Position text above the block
        cv::Point textPos(block.boundingBox.x, block.boundingBox.y - 10);
        if (textPos.y < 20) textPos.y = block.boundingBox.y + block.boundingBox.height + 20;
        
        putTextWithBackground(image, text.str(), textPos, 0.5, color);
        
        // Add dimensions
        std::stringstream dimText;
        cv::Size2f size = block.rotatedRect.size;
        dimText << "W: " << std::fixed << std::setprecision(1) << size.width 
                << " H: " << size.height;
        
        cv::Point dimPos(block.boundingBox.x, textPos.y + 20);
        putTextWithBackground(image, dimText.str(), dimPos, 0.4, cv::Scalar(200, 200, 200));
        
        // Add center coordinates
        std::stringstream centerText;
        centerText << "(" << (int)block.center.x << ", " << (int)block.center.y << ")";
        
        cv::Point centerTextPos(block.center.x + 15, block.center.y - 15);
        putTextWithBackground(image, centerText.str(), centerTextPos, 0.4, 
                            cv::Scalar(200, 200, 200));
    }
}

void MeasureDisplay::putTextWithBackground(cv::Mat& image, const std::string& text,
                                              const cv::Point& position, double fontScale,
                                              const cv::Scalar& textColor,
                                              const cv::Scalar& bgColor) {
    // Get text size
    int baseline = 0;
    cv::Size textSize = cv::getTextSize(text, fontFace, fontScale, thickness, &baseline);
    
    // Draw background rectangle
    cv::rectangle(image, 
                  cv::Rect(position.x - 5, position.y - textSize.height - 5,
                          textSize.width + 10, textSize.height + baseline + 10),
                  bgColor, -1);
    
    // Draw text
    cv::putText(image, text, 
                cv::Point(position.x, position.y + textSize.height/2),
                fontFace, fontScale, textColor, thickness);
}

cv::Mat MeasureDisplay::createReport(const cv::Mat& image, 
                                        const std::vector<BlockMeasure>& blocks) {
    // Create a larger canvas for the report
    int reportWidth = image.cols * 2;
    int reportHeight = std::max(image.rows, 300);
    cv::Mat report = cv::Mat::zeros(reportHeight, reportWidth, CV_8UC3);
    
    // Place original image on left
    cv::Mat imageWithMeasure = displayMeasure(image, blocks, true);
    cv::Rect leftRegion(0, 0, image.cols, image.rows);
    imageWithMeasure.copyTo(report(leftRegion));
    
    // Create statistics panel on right
    cv::Rect rightRegion(image.cols, 0, image.cols, reportHeight);
    cv::Mat statsPanel = cv::Mat::zeros(reportHeight, image.cols, CV_8UC3);
    statsPanel.setTo(cv::Scalar(240, 240, 240));
    
    // Add statistics header
    cv::putText(statsPanel, "BLOCK Measure REPORT", 
                cv::Point(20, 40), fontFace, 0.8, cv::Scalar(0, 0, 0), 2);
    
    // Add summary statistics
    std::stringstream stats;
    stats << "Total Blocks: " << blocks.size() << "\n\n";
    
    if (!blocks.empty()) {
        // Find largest and smallest
        double maxArea = 0, minArea = 1e9;
        int largestID = 0, smallestID = 0;
        
        for (size_t i = 0; i < blocks.size(); ++i) {
            if (blocks[i].area > maxArea) {
                maxArea = blocks[i].area;
                largestID = i + 1;
            }
            if (blocks[i].area < minArea) {
                minArea = blocks[i].area;
                smallestID = i + 1;
            }
        }
        
        stats << "Largest Block: #" << largestID 
              << " (" << std::fixed << std::setprecision(1) << maxArea << " px²)\n";
        stats << "Smallest Block: #" << smallestID 
              << " (" << std::fixed << std::setprecision(1) << minArea << " px²)\n\n";
        
        // Add details for each block
        stats << "DETAILED Measure:\n";
        stats << "ID | Type | Area | Width | Height | Center\n";
        stats << "------------------------------------------\n";
        
        for (size_t i = 0; i < blocks.size(); ++i) {
            const auto& block = blocks[i];
            cv::Size2f size = block.rotatedRect.size;
            
            stats << std::setw(2) << i + 1 << " | "
                  << std::setw(12) << block.type << " | "
                  << std::setw(6) << std::fixed << std::setprecision(1) << block.area << " | "
                  << std::setw(5) << std::fixed << std::setprecision(1) << size.width << " | "
                  << std::setw(6) << std::fixed << std::setprecision(1) << size.height << " | "
                  << "(" << (int)block.center.x << "," << (int)block.center.y << ")\n";
        }
    }
    
    // Split text into lines and display
    std::stringstream ss(stats.str());
    std::string line;
    int y = 80;
    int lineHeight = 25;
    
    while (std::getline(ss, line)) {
        cv::putText(statsPanel, line, cv::Point(20, y), 
                   fontFace, 0.4, cv::Scalar(0, 0, 0), 1);
        y += lineHeight;
    }
    
    // Copy stats panel to report
    statsPanel.copyTo(report(rightRegion));
    
    return report;
}

void MeasureDisplay::drawScale(cv::Mat& image, double pixelsPerMM, 
                                  const cv::Point& start) {
    int scaleLength = 100; // pixels
    int mmLength = (int)(scaleLength / pixelsPerMM);
    
    // Draw scale line
    cv::Point end(start.x + scaleLength, start.y);
    cv::line(image, start, end, cv::Scalar(255, 255, 255), 3);
    cv::line(image, cv::Point(start.x, start.y - 10), 
            cv::Point(start.x, start.y + 10), cv::Scalar(255, 255, 255), 2);
    cv::line(image, cv::Point(end.x, end.y - 10), 
            cv::Point(end.x, end.y + 10), cv::Scalar(255, 255, 255), 2);
    
    // Add label
    std::stringstream label;
    label << mmLength << " mm";
    cv::putText(image, label.str(), cv::Point(start.x + 20, start.y - 15),
               fontFace, 0.5, cv::Scalar(255, 255, 255), 1);
    
    // Add Measure note
    std::stringstream note;
    note << "Scale: " << std::fixed << std::setprecision(2) 
         << pixelsPerMM << " pixels/mm";
    cv::putText(image, note.str(), cv::Point(start.x, start.y + 30),
               fontFace, 0.4, cv::Scalar(200, 200, 200), 1);
}

void MeasureDisplay::drawGrid(cv::Mat& image, int gridSize) {
    cv::Mat gridImage = image.clone();
    
    // Draw vertical lines
    for (int x = 0; x < image.cols; x += gridSize) {
        cv::line(gridImage, cv::Point(x, 0), cv::Point(x, image.rows),
                cv::Scalar(100, 100, 100), 1);
    }
    
    // Draw horizontal lines
    for (int y = 0; y < image.rows; y += gridSize) {
        cv::line(gridImage, cv::Point(0, y), cv::Point(image.cols, y),
                cv::Scalar(100, 100, 100), 1);
    }
    
    // Add grid labels
    for (int x = 0; x < image.cols; x += gridSize * 5) {
        std::string label = std::to_string(x);
        cv::putText(gridImage, label, cv::Point(x + 5, 20),
                   fontFace, 0.4, cv::Scalar(150, 150, 150), 1);
    }
    
    for (int y = 0; y < image.rows; y += gridSize * 5) {
        std::string label = std::to_string(y);
        cv::putText(gridImage, label, cv::Point(5, y + 15),
                   fontFace, 0.4, cv::Scalar(150, 150, 150), 1);
    }
    
    // Apply grid with transparency
    cv::addWeighted(image, 0.7, gridImage, 0.3, 0, image);

}

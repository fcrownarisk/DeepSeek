#include <iostream>
#include <opencv2/opencv.hpp>
#include "BlockDetector.h"
#include "MeasureDisplay.h"

// Function prototypes
void processImage(const std::string& imagePath);
void processCamera();
void createTestImage();

int main(int argc, char** argv) {
    std::cout << "=========================================" << std::endl;
    std::cout << "   OpenCV Block Measure System      " << std::endl;
    std::cout << "=========================================" << std::endl;
    std::cout << std::endl;
    
    int choice;
    std::cout << "Select input source:" << std::endl;
    std::cout << "1. Process image file" << std::endl;
    std::cout << "2. Use webcam" << std::endl;
    std::cout << "3. Create test image" << std::endl;
    std::cout << "4. Exit" << std::endl;
    std::cout << "Enter choice (1-4): ";
    std::cin >> choice;
    
    switch (choice) {
        case 1: {
            std::string imagePath;
            std::cout << "Enter image path: ";
            std::cin >> imagePath;
            processImage(imagePath);
            break;
        }
        case 2:
            processCamera();
            break;
        case 3:
            createTestImage();
            break;
        case 4:
            std::cout << "Exiting..." << std::endl;
            break;
        default:
            std::cout << "Invalid choice!" << std::endl;
    }
    
    return 0;
}

void processImage(const std::string& imagePath) {
    // Load image
    cv::Mat image = cv::imread(imagePath);
    
    if (image.empty()) {
        std::cerr << "Error: Could not load image: " << imagePath << std::endl;
        
        // Try default test image
        std::cout << "Creating test image instead..." << std::endl;
        createTestImage();
        return;
    }
    
    // Create detector and display objects
    BlockDetector detector;
    MeasureDisplay display;
    
    // Set detection parameters (adjust as needed)
    detector.setPreprocessingParams(7, 30, 100);
    detector.setMorphologyParams(5, 3);
    
    // Detect blocks
    std::cout << "Detecting blocks..." << std::endl;
    std::vector<BlockMeasure> blocks = detector.detectBlocks(image, false);
    
    if (blocks.empty()) {
        std::cout << "No blocks detected!" << std::endl;
        return;
    }
    
    std::cout << "Detected " << blocks.size() << " blocks." << std::endl;
    
    // Display results
    cv::Mat result = display.displayMeasures(image, blocks, true);
    
    // Create detailed report
    cv::Mat report = display.createReport(image, blocks);
    
    // Add scale to report (assuming known pixels/mm ratio)
    display.drawScale(result, 10.0); // 10 pixels per mm
    
    // Show results
    cv::imshow("Original Image", image);
    cv::imshow("Block Measures", result);
    cv::imshow("Measure Report", report);
    
    // Save results
    cv::imwrite("Measure_result.jpg", result);
    cv::imwrite("Measure_report.jpg", report);
    
    // Save Measures to CSV
    detector.saveMeasuresToCSV(blocks, "Measures.csv");
    
    // Print statistics
    BlockMeasure largest = detector.findLargestBlock(blocks);
    BlockMeasure smallest = detector.findSmallestBlock(blocks);
    
    std::cout << "\n=== Measure Statistics ===" << std::endl;
    std::cout << "Largest block: Area = " << largest.area << " px²" << std::endl;
    std::cout << "Smallest block: Area = " << smallest.area << " px²" << std::endl;
    
    double totalArea = 0;
    for (const auto& block : blocks) {
        totalArea += block.area;
    }
    std::cout << "Total area: " << totalArea << " px²" << std::endl;
    std::cout << "Average area: " << totalArea / blocks.size() << " px²" << std::endl;
    
    cv::waitKey(0);
}

void processCamera() {
    cv::VideoCapture cap(0);
    
    if (!cap.isOpened()) {
        std::cerr << "Error: Could not open camera!" << std::endl;
        return;
    }
    
    BlockDetector detector;
    MeasureDisplay display;
    
    std::cout << "Press 'q' to quit, 's' to save current frame" << std::endl;
    std::cout << "Press 'd' to toggle detection display" << std::endl;
    
    bool showDetection = true;
    int frameCount = 0;
    
    while (true) {
        cv::Mat frame;
        cap >> frame;
        
        if (frame.empty()) {
            std::cerr << "Error: Empty frame!" << std::endl;
            break;
        }
        
        if (showDetection && frameCount % 5 == 0) {
            // Detect blocks every 5 frames
            std::vector<BlockMeasure> blocks = detector.detectBlocks(frame, false);
            
            if (!blocks.empty()) {
                frame = display.displayMeasures(frame, blocks, false);
                
                // Display block count
                std::stringstream info;
                info << "Blocks: " << blocks.size();
                cv::putText(frame, info.str(), cv::Point(20, 30),
                           cv::FONT_HERSHEY_SIMPLEX, 1, cv::Scalar(0, 255, 0), 2);
            }
        }
        
        // Add FPS display
        std::stringstream fpsText;
        fpsText << "FPS: " << cap.get(cv::CAP_PROP_FPS);
        cv::putText(frame, fpsText.str(), cv::Point(frame.cols - 150, 30),
                   cv::FONT_HERSHEY_SIMPLEX, 0.7, cv::Scalar(0, 0, 255), 2);
        
        cv::imshow("Camera - Block Detection", frame);
        
        char key = cv::waitKey(1);
        if (key == 'q' || key == 27) { // 'q' or ESC
            break;
        } else if (key == 's') {
            // Save current frame
            std::string filename = "capture_" + std::to_string(time(0)) + ".jpg";
            cv::imwrite(filename, frame);
            std::cout << "Saved: " << filename << std::endl;
        } else if (key == 'd') {
            showDetection = !showDetection;
            std::cout << "Detection display: " << (showDetection ? "ON" : "OFF") << std::endl;
        }
        
        frameCount++;
    }
    
    cap.release();
    cv::destroyAllWindows();
}

void createTestImage() {
    // Create a test image with geometric shapes
    cv::Mat testImage = cv::Mat::zeros(600, 800, CV_8UC3);
    testImage.setTo(cv::Scalar(50, 50, 50)); // Gray background
    
    // Draw various shapes as test blocks
    cv::RNG rng(time(0));
    
    std::cout << "Creating test image with random blocks..." << std::endl;
    
    for (int i = 0; i < 8; i++) {
        int x = rng.uniform(50, 700);
        int y = rng.uniform(50, 500);
        int width = rng.uniform(30, 120);
        int height = rng.uniform(30, 120);
        
        // Random color
        cv::Scalar color(rng.uniform(0, 255), 
                        rng.uniform(0, 255), 
                        rng.uniform(0, 255));
        
        // Draw filled rectangle
        cv::rectangle(testImage, 
                     cv::Rect(x, y, width, height),
                     color, -1);
        
        // Add slight rotation effect by drawing a rotated rectangle outline
        cv::Point center(x + width/2, y + height/2);
        cv::Size size(width, height);
        float angle = rng.uniform(-30.0, 30.0);
        
        cv::RotatedRect rotatedRect(center, size, angle);
        cv::Point2f vertices[4];
        rotatedRect.points(vertices);
        
        for (int j = 0; j < 4; j++) {
            cv::line(testImage, vertices[j], vertices[(j+1)%4],
                    cv::Scalar(255, 255, 255), 2);
        }
    }
    
    // Add some noise to simulate real conditions
    cv::Mat noise = cv::Mat(testImage.size(), testImage.type());
    cv::randn(noise, 0, 15);
    testImage += noise;
    
    // Add grid for reference
    for (int x = 0; x < testImage.cols; x += 50) {
        cv::line(testImage, cv::Point(x, 0), cv::Point(x, testImage.rows),
                cv::Scalar(100, 100, 100), 1);
    }
    for (int y = 0; y < testImage.rows; y += 50) {
        cv::line(testImage, cv::Point(0, y), cv::Point(testImage.cols, y),
                cv::Scalar(100, 100, 100), 1);
    }
    
    // Save and process the test image
    cv::imwrite("test_blocks.jpg", testImage);
    std::cout << "Test image saved as 'test_blocks.jpg'" << std::endl;
    processImage("test_blocks.jpg");
}
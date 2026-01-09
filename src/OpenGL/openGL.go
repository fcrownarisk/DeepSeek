package main

import (
	"fmt"
	"math"
	"runtime"
	"time"

	"github.com/go-gl/gl/v4.6-core/gl"
	"github.com/go-gl/glfw/v3.3/glfw"
	"github.com/go-gl/mathgl/mgl32"
)

const (
	windowWidth  = 1024
	windowHeight = 768
	windowTitle  = "OpenGL 3D Coordinate System - Go"
)

// Camera parameters
var (
	cameraPos   = mgl32.Vec3{3.0, 3.0, 3.0}
	cameraFront = mgl32.Vec3{0.0, 0.0, -1.0}
	cameraUp    = mgl32.Vec3{0.0, 1.0, 0.0}
	
	yaw         = float32(-90.0)
	pitch       = float32(0.0)
	lastX       = float32(windowWidth / 2)
	lastY       = float32(windowHeight / 2)
	firstMouse  = true
	
	fov         = float32(45.0)
	
	// Projection and view matrices
	projection mgl32.Mat4
	view       mgl32.Mat4
	
	// Movement speed
	cameraSpeed = float32(2.5)
	
	// Frame timing
	lastFrame float64 = 0
	deltaTime float32 = 0
)

func main() {
	// Lock to main thread (OpenGL requirement)
	runtime.LockOSThread()
	
	// Initialize GLFW
	if err := glfw.Init(); err != nil {
		panic(fmt.Sprintf("Failed to initialize GLFW: %v", err))
	}
	defer glfw.Terminate()
	
	// Configure GLFW
	glfw.WindowHint(glfw.ContextVersionMajor, 4)
	glfw.WindowHint(glfw.ContextVersionMinor, 6)
	glfw.WindowHint(glfw.OpenGLProfile, glfw.OpenGLCoreProfile)
	glfw.WindowHint(glfw.OpenGLForwardCompatible, glfw.True)
	glfw.WindowHint(glfw.Resizable, glfw.True)
	
	// Create window
	window, err := glfw.CreateWindow(windowWidth, windowHeight, windowTitle, nil, nil)
	if err != nil {
		panic(fmt.Sprintf("Failed to create GLFW window: %v", err))
	}
	window.MakeContextCurrent()
	
	// Initialize OpenGL
	if err := gl.Init(); err != nil {
		panic(fmt.Sprintf("Failed to initialize OpenGL: %v", err))
	}
	
	// Set OpenGL version info
	version := gl.GoStr(gl.GetString(gl.VERSION))
	fmt.Printf("OpenGL Version: %s\n", version)
	
	// Configure OpenGL
	gl.Viewport(0, 0, windowWidth, windowHeight)
	gl.Enable(gl.DEPTH_TEST)
	gl.ClearColor(0.1, 0.1, 0.1, 1.0)
	
	// Enable line anti-aliasing
	gl.Enable(gl.LINE_SMOOTH)
	gl.Hint(gl.LINE_SMOOTH_HINT, gl.NICEST)
	gl.LineWidth(2.0)
	
	// Compile shaders
	shaderProgram := compileShaders()
	
	// Create coordinate system VAO/VBO
	coordVAO, coordVBO := createCoordinateSystem()
	
	// Create grid VAO/VBO
	gridVAO, gridVBO := createGrid()
	
	// Create cube VAO/VBO (for reference)
	cubeVAO, cubeVBO := createCube()
	
	// Set callbacks
	window.SetFramebufferSizeCallback(framebufferSizeCallback)
	window.SetCursorPosCallback(mouseCallback)
	window.SetScrollCallback(scrollCallback)
	window.SetKeyCallback(keyCallback)
	
	// Enable cursor capture
	window.SetInputMode(glfw.CursorMode, glfw.CursorDisabled)
	
	// Main render loop
	for !window.ShouldClose() {
		// Calculate delta time
		currentFrame := glfw.GetTime()
		deltaTime = float32(currentFrame - lastFrame)
		lastFrame = currentFrame
		
		// Process input
		processInput(window)
		
		// Clear buffers
		gl.Clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT)
		
		// Use shader program
		gl.UseProgram(shaderProgram)
		
		// Update projection matrix
		projection = mgl32.Perspective(
			mgl32.DegToRad(fov),
			float32(windowWidth)/float32(windowHeight),
			0.1, 100.0,
		)
		
		// Update view matrix
		target := cameraPos.Add(cameraFront)
		view = mgl32.LookAtV(cameraPos, target, cameraUp)
		
		// Set matrices in shader
		projectionLoc := gl.GetUniformLocation(shaderProgram, gl.Str("projection\x00"))
		viewLoc := gl.GetUniformLocation(shaderProgram, gl.Str("view\x00"))
		modelLoc := gl.GetUniformLocation(shaderProgram, gl.Str("model\x00"))
		
		gl.UniformMatrix4fv(projectionLoc, 1, false, &projection[0])
		gl.UniformMatrix4fv(viewLoc, 1, false, &view[0])
		
		// Draw coordinate system
		gl.BindVertexArray(coordVAO)
		model := mgl32.Ident4()
		gl.UniformMatrix4fv(modelLoc, 1, false, &model[0])
		gl.DrawArrays(gl.LINES, 0, 6)
		
		// Draw grid
		gl.BindVertexArray(gridVAO)
		gl.UniformMatrix4fv(modelLoc, 1, false, &model[0])
		gl.DrawArrays(gl.LINES, 0, 44) // 22 lines * 2 vertices = 44
		
		// Draw unit cube at origin
		gl.BindVertexArray(cubeVAO)
		model = mgl32.Scale3D(0.5, 0.5, 0.5) // Smaller cube
		gl.UniformMatrix4fv(modelLoc, 1, false, &model[0])
		gl.DrawArrays(gl.LINES, 0, 24) // 12 lines * 2 vertices = 24
		
		// Swap buffers and poll events
		window.SwapBuffers()
		glfw.PollEvents()
		
		// Update window title with FPS and camera info
		fps := int(1.0 / deltaTime)
		window.SetTitle(fmt.Sprintf("%s | FPS: %d | Pos: (%.2f, %.2f, %.2f)", 
			windowTitle, fps, cameraPos[0], cameraPos[1], cameraPos[2]))
	}
	
	// Cleanup
	gl.DeleteVertexArrays(1, &coordVAO)
	gl.DeleteBuffers(1, &coordVBO)
	gl.DeleteVertexArrays(1, &gridVAO)
	gl.DeleteBuffers(1, &gridVBO)
	gl.DeleteVertexArrays(1, &cubeVAO)
	gl.DeleteBuffers(1, &cubeVBO)
	gl.DeleteProgram(shaderProgram)
}

func compileShaders() uint32 {
	// Vertex shader source
	vertexShaderSource := `#version 460 core
layout (location = 0) in vec3 aPos;
layout (location = 1) in vec3 aColor;

uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;

out vec3 Color;

void main() {
    gl_Position = projection * view * model * vec4(aPos, 1.0);
    Color = aColor;
}` + "\x00"

	// Fragment shader source
	fragmentShaderSource := `#version 460 core
in vec3 Color;
out vec4 FragColor;

void main() {
    FragColor = vec4(Color, 1.0);
}` + "\x00"

	// Compile vertex shader
	vertexShader := gl.CreateShader(gl.VERTEX_SHADER)
	csources, free := gl.Strs(vertexShaderSource)
	gl.ShaderSource(vertexShader, 1, csources, nil)
	free()
	gl.CompileShader(vertexShader)
	
	// Check vertex shader
	var success int32
	gl.GetShaderiv(vertexShader, gl.COMPILE_STATUS, &success)
	if success == gl.FALSE {
		var logLength int32
		gl.GetShaderiv(vertexShader, gl.INFO_LOG_LENGTH, &logLength)
		log := make([]byte, logLength)
		gl.GetShaderInfoLog(vertexShader, logLength, nil, &log[0])
		panic(fmt.Sprintf("Vertex shader compilation failed: %s", string(log)))
	}
	
	// Compile fragment shader
	fragmentShader := gl.CreateShader(gl.FRAGMENT_SHADER)
	fsources, free := gl.Strs(fragmentShaderSource)
	gl.ShaderSource(fragmentShader, 1, fsources, nil)
	free()
	gl.CompileShader(fragmentShader)
	
	// Check fragment shader
	gl.GetShaderiv(fragmentShader, gl.COMPILE_STATUS, &success)
	if success == gl.FALSE {
		var logLength int32
		gl.GetShaderiv(fragmentShader, gl.INFO_LOG_LENGTH, &logLength)
		log := make([]byte, logLength)
		gl.GetShaderInfoLog(fragmentShader, logLength, nil, &log[0])
		panic(fmt.Sprintf("Fragment shader compilation failed: %s", string(log)))
	}
	
	// Link shader program
	shaderProgram := gl.CreateProgram()
	gl.AttachShader(shaderProgram, vertexShader)
	gl.AttachShader(shaderProgram, fragmentShader)
	gl.LinkProgram(shaderProgram)
	
	// Check linking
	gl.GetProgramiv(shaderProgram, gl.LINK_STATUS, &success)
	if success == gl.FALSE {
		var logLength int32
		gl.GetProgramiv(shaderProgram, gl.INFO_LOG_LENGTH, &logLength)
		log := make([]byte, logLength)
		gl.GetProgramInfoLog(shaderProgram, logLength, nil, &log[0])
		panic(fmt.Sprintf("Shader program linking failed: %s", string(log)))
	}
	
	// Cleanup shaders
	gl.DeleteShader(vertexShader)
	gl.DeleteShader(fragmentShader)
	
	return shaderProgram
}

func createCoordinateSystem() (uint32, uint32) {
	// Coordinate system vertices (position + color)
	// X-axis: Red, Y-axis: Green, Z-axis: Blue
	vertices := []float32{
		// X-axis (Red)
		0.0, 0.0, 0.0, 1.0, 0.0, 0.0,
		5.0, 0.0, 0.0, 1.0, 0.0, 0.0,
		
		// Y-axis (Green)
		0.0, 0.0, 0.0, 0.0, 1.0, 0.0,
		0.0, 5.0, 0.0, 0.0, 1.0, 0.0,
		
		// Z-axis (Blue)
		0.0, 0.0, 0.0, 0.0, 0.0, 1.0,
		0.0, 0.0, 5.0, 0.0, 0.0, 1.0,
	}
	
	var VAO, VBO uint32
	gl.GenVertexArrays(1, &VAO)
	gl.GenBuffers(1, &VBO)
	
	gl.BindVertexArray(VAO)
	
	gl.BindBuffer(gl.ARRAY_BUFFER, VBO)
	gl.BufferData(gl.ARRAY_BUFFER, len(vertices)*4, gl.Ptr(vertices), gl.STATIC_DRAW)
	
	// Position attribute
	gl.VertexAttribPointer(0, 3, gl.FLOAT, false, 6*4, gl.PtrOffset(0))
	gl.EnableVertexAttribArray(0)
	
	// Color attribute
	gl.VertexAttribPointer(1, 3, gl.FLOAT, false, 6*4, gl.PtrOffset(3*4))
	gl.EnableVertexAttribArray(1)
	
	gl.BindBuffer(gl.ARRAY_BUFFER, 0)
	gl.BindVertexArray(0)
	
	return VAO, VBO
}

func createGrid() (uint32, uint32) {
	// Create a grid in the XZ plane
	var vertices []float32
	gridSize := 10
	gridColor := []float32{0.3, 0.3, 0.3}
	
	// Add grid lines
	for i := -gridSize; i <= gridSize; i++ {
		// Lines along X direction
		vertices = append(vertices,
			float32(-gridSize), 0.0, float32(i), gridColor[0], gridColor[1], gridColor[2],
			float32(gridSize), 0.0, float32(i), gridColor[0], gridColor[1], gridColor[2],
		)
		// Lines along Z direction
		vertices = append(vertices,
			float32(i), 0.0, float32(-gridSize), gridColor[0], gridColor[1], gridColor[2],
			float32(i), 0.0, float32(gridSize), gridColor[0], gridColor[1], gridColor[2],
		)
	}
	
	var VAO, VBO uint32
	gl.GenVertexArrays(1, &VAO)
	gl.GenBuffers(1, &VBO)
	
	gl.BindVertexArray(VAO)
	
	gl.BindBuffer(gl.ARRAY_BUFFER, VBO)
	gl.BufferData(gl.ARRAY_BUFFER, len(vertices)*4, gl.Ptr(vertices), gl.STATIC_DRAW)
	
	// Position attribute
	gl.VertexAttribPointer(0, 3, gl.FLOAT, false, 6*4, gl.PtrOffset(0))
	gl.EnableVertexAttribArray(0)
	
	// Color attribute
	gl.VertexAttribPointer(1, 3, gl.FLOAT, false, 6*4, gl.PtrOffset(3*4))
	gl.EnableVertexAttribArray(1)
	
	gl.BindBuffer(gl.ARRAY_BUFFER, 0)
	gl.BindVertexArray(0)
	
	return VAO, VBO
}

func createCube() (uint32, uint32) {
	// Unit cube wireframe vertices (position + color)
	// Color: Yellow for visibility
	vertices := []float32{
		// Front face
		-1.0, -1.0,  1.0, 1.0, 1.0, 0.0,
		 1.0, -1.0,  1.0, 1.0, 1.0, 0.0,
		 1.0, -1.0,  1.0, 1.0, 1.0, 0.0,
		 1.0,  1.0,  1.0, 1.0, 1.0, 0.0,
		 1.0,  1.0,  1.0, 1.0, 1.0, 0.0,
		-1.0,  1.0,  1.0, 1.0, 1.0, 0.0,
		-1.0,  1.0,  1.0, 1.0, 1.0, 0.0,
		-1.0, -1.0,  1.0, 1.0, 1.0, 0.0,
		
		// Back face
		-1.0, -1.0, -1.0, 1.0, 1.0, 0.0,
		 1.0, -1.0, -1.0, 1.0, 1.0, 0.0,
		 1.0, -1.0, -1.0, 1.0, 1.0, 0.0,
		 1.0,  1.0, -1.0, 1.0, 1.0, 0.0,
		 1.0,  1.0, -1.0, 1.0, 1.0, 0.0,
		-1.0,  1.0, -1.0, 1.0, 1.0, 0.0,
		-1.0,  1.0, -1.0, 1.0, 1.0, 0.0,
		-1.0, -1.0, -1.0, 1.0, 1.0, 0.0,
		
		// Connecting edges
		-1.0, -1.0,  1.0, 1.0, 1.0, 0.0,
		-1.0, -1.0, -1.0, 1.0, 1.0, 0.0,
		 1.0, -1.0,  1.0, 1.0, 1.0, 0.0,
		 1.0, -1.0, -1.0, 1.0, 1.0, 0.0,
		 1.0,  1.0,  1.0, 1.0, 1.0, 0.0,
		 1.0,  1.0, -1.0, 1.0, 1.0, 0.0,
		-1.0,  1.0,  1.0, 1.0, 1.0, 0.0,
		-1.0,  1.0, -1.0, 1.0, 1.0, 0.0,
	}
	
	var VAO, VBO uint32
	gl.GenVertexArrays(1, &VAO)
	gl.GenBuffers(1, &VBO)
	
	gl.BindVertexArray(VAO)
	
	gl.BindBuffer(gl.ARRAY_BUFFER, VBO)
	gl.BufferData(gl.ARRAY_BUFFER, len(vertices)*4, gl.Ptr(vertices), gl.STATIC_DRAW)
	
	// Position attribute
	gl.VertexAttribPointer(0, 3, gl.FLOAT, false, 6*4, gl.PtrOffset(0))
	gl.EnableVertexAttribArray(0)
	
	// Color attribute
	gl.VertexAttribPointer(1, 3, gl.FLOAT, false, 6*4, gl.PtrOffset(3*4))
	gl.EnableVertexAttribArray(1)
	
	gl.BindBuffer(gl.ARRAY_BUFFER, 0)
	gl.BindVertexArray(0)
	
	return VAO, VBO
}

func processInput(window *glfw.Window) {
	// Calculate camera movement based on delta time
	actualSpeed := cameraSpeed * deltaTime
	
	// WASD movement
	if window.GetKey(glfw.KeyW) == glfw.Press {
		cameraPos = cameraPos.Add(cameraFront.Mul(actualSpeed))
	}
	if window.GetKey(glfw.KeyS) == glfw.Press {
		cameraPos = cameraPos.Sub(cameraFront.Mul(actualSpeed))
	}
	if window.GetKey(glfw.KeyA) == glfw.Press {
		cameraPos = cameraPos.Sub(cameraFront.Cross(cameraUp).Normalize().Mul(actualSpeed))
	}
	if window.GetKey(glfw.KeyD) == glfw.Press {
		cameraPos = cameraPos.Add(cameraFront.Cross(cameraUp).Normalize().Mul(actualSpeed))
	}
	
	// Space/Shift for vertical movement
	if window.GetKey(glfw.KeySpace) == glfw.Press {
		cameraPos = cameraPos.Add(cameraUp.Mul(actualSpeed))
	}
	if window.GetKey(glfw.KeyLeftShift) == glfw.Press {
		cameraPos = cameraPos.Sub(cameraUp.Mul(actualSpeed))
	}
	
	// Reset camera position
	if window.GetKey(glfw.KeyR) == glfw.Press {
		cameraPos = mgl32.Vec3{3.0, 3.0, 3.0}
		yaw = -90.0
		pitch = 0.0
		updateCameraVectors()
	}
	
	// Quit
	if window.GetKey(glfw.KeyEscape) == glfw.Press {
		window.SetShouldClose(true)
	}
	
	// Speed control
	if window.GetKey(glfw.KeyUp) == glfw.Press {
		cameraSpeed += 0.5
		if cameraSpeed > 10.0 {
			cameraSpeed = 10.0
		}
	}
	if window.GetKey(glfw.KeyDown) == glfw.Press {
		cameraSpeed -= 0.5
		if cameraSpeed < 0.5 {
			cameraSpeed = 0.5
		}
	}
}

func mouseCallback(window *glfw.Window, xpos, ypos float64) {
	xposFloat := float32(xpos)
	yposFloat := float32(ypos)
	
	if firstMouse {
		lastX = xposFloat
		lastY = yposFloat
		firstMouse = false
	}
	
	xoffset := xposFloat - lastX
	yoffset := lastY - yposFloat // Reversed since y-coordinates go from bottom to top
	lastX = xposFloat
	lastY = yposFloat
	
	sensitivity := float32(0.1)
	xoffset *= sensitivity
	yoffset *= sensitivity
	
	yaw += xoffset
	pitch += yoffset
	
	// Constrain pitch
	if pitch > 89.0 {
		pitch = 89.0
	}
	if pitch < -89.0 {
		pitch = -89.0
	}
	
	updateCameraVectors()
}

func scrollCallback(window *glfw.Window, xoffset, yoffset float64) {
	fov -= float32(yoffset)
	if fov < 1.0 {
		fov = 1.0
	}
	if fov > 90.0 {
		fov = 90.0
	}
}

func updateCameraVectors() {
	// Calculate front vector
	front := mgl32.Vec3{
		float32(math.Cos(float64(mgl32.DegToRad(yaw))) * math.Cos(float64(mgl32.DegToRad(pitch)))),
		float32(math.Sin(float64(mgl32.DegToRad(pitch)))),
		float32(math.Sin(float64(mgl32.DegToRad(yaw))) * math.Cos(float64(mgl32.DegToRad(pitch)))),
	}
	cameraFront = front.Normalize()
}

func framebufferSizeCallback(window *glfw.Window, width, height int) {
	gl.Viewport(0, 0, int32(width), int32(height))
}

func keyCallback(window *glfw.Window, key glfw.Key, scancode int, action glfw.Action, mods glfw.ModifierKey) {
	// Toggle cursor mode with Tab key
	if key == glfw.KeyTab && action == glfw.Press {
		if window.GetInputMode(glfw.CursorMode) == glfw.CursorDisabled {
			window.SetInputMode(glfw.CursorMode, glfw.CursorNormal)
			firstMouse = true
		} else {
			window.SetInputMode(glfw.CursorMode, glfw.CursorDisabled)
		}
	}
}
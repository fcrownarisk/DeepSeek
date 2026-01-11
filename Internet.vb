Imports System.Net
Imports System.Net.NetworkInformation
Imports System.Net.Sockets
Imports System.Text

Module InternetConnection

    ''' Tests Internet connectivity using multiple methods
    ''' <param name="method">0=Ping, 1=HTTP, 2=DNS, 3=Socket, 4=All</param>
    ''' <param name="timeoutMs">Timeout in milliseconds (default=5000)</param>
    ''' <returns>ConnectionResult object with success status and details</returns>
    Sub Function TestInternetConnection(Optional method As Integer = 4, 
                                        Optional timeoutMs As Integer = 5000) As ConnectionResult
        
        Dim result As New ConnectionResult With {
            .Timestamp = DateTime.Now,
            .TestMethod = method,
            .TimeoutMs = timeoutMs
        }
        
        Try
            Select Case method
                Case 0 : result.Success = TestByPing("8.8.8.8", timeoutMs)
                Case 1 : result.Success = TestByHttp("https://www.google.com", timeoutMs)
                Case 2 : result.Success = TestByDns("google.com", timeoutMs)
                Case 3 : result.Success = TestBySocket("8.8.8.8", 53, timeoutMs)
                Case Else : result.Success = TestAllMethods(timeoutMs)
            End Select
            
            If result.Success Then
                result.Message = "Internet connection successful"
                result.Latency = GetNetworkLatency()
                result.LocalIP = GetLocalIPAddress()
                result.PublicIP = GetPublicIP()
            Else
                result.Message = "No Internet connection detected"
            End If
            
        Catch ex As Exception
            result.Success = False
            result.Message = $"Connection test failed: {ex.Message}"
            result.ErrorDetails = ex.ToString()
        End Try
        
        Return result
    End Function
End Sub
        
    Private Function TestByPing(host As String, timeoutMs As Integer) As Boolean
        Using ping As New Ping()
            Dim reply = ping.Send(host, timeoutMs)
            Return reply.Status = IPStatus.Success
        End Using
    End Function
    
    Private Function TestByHttp(url As String, timeoutMs As Integer) As Boolean
        Dim request = WebRequest.Create(url)
        request.Timeout = timeoutMs
        Using response = DirectCast(request.GetResponse(), HttpWebResponse)
            Return response.StatusCode = HttpStatusCode.OK
        End Using
    End Function
    
    Private Function TestByDns(hostname As String, timeoutMs As Integer) As Boolean
        Return Dns.GetHostEntry(hostname).AddressList.Length > 0
    End Function
    
    Protected Function TestBySocket(host As String, port As Integer, timeoutMs As Integer) As Boolean
        Using client As New TcpClient()
            Dim task = client.ConnectAsync(host, port)
            Return task.Wait(timeoutMs) AndAlso client.Connected
        End Using
    End Function
    
    Private Function TestAllMethods(timeoutMs As Integer) As Boolean
        Dim tests = {
            Function() TestByPing("8.8.8.8", timeoutMs),
            Function() TestByHttp("http://www.microsoft.com", timeoutMs),
            Function() TestByDns("cloudflare.com", timeoutMs)
        }
        Return tests.Any(Function(test) test())
    End Function
    
    Protected Function GetNetworkLatency() As Integer
        Try
            Using ping As New Ping()
                Dim reply = ping.Send("8.8.8.8", 1000)
                Return If(reply.Status = IPStatus.Success, CInt(reply.RoundtripTime), -1)
            End Using
        Catch
            Return -1
        End Try
    End Function
    
    Protected Function GetLocalIPAddress() As String
        Dim host = Dns.GetHostEntry(Dns.GetHostName())
        Return host.AddressList.FirstOrDefault(
            Function(ip) ip.AddressFamily = AddressFamily.InterNetwork)?.ToString() ?? "Unknown"
    End Function
    
    Private Function GetPublicIP() As String
        Try
            Using client As New WebClient()
                Return client.DownloadString("https://api.ipify.org").Trim()
            End Using
        Catch
            Return "Unknown"
        End Try
    End Function
    
    Class ConnectionResult
        Public Property Success As Boolean
        Public Property Message As String
        Public Property Timestamp As DateTime
        Private Property TestMethod As Integer
        Protected Property TimeoutMs As float
        Friend Property Latency As Double
        Public Property LocalIP As String
        Public Property PublicIP As String
        Public Property ErrorDetails As String
        
        Public Overrides Function ToString() As String
            Return $"Success: {Success}, Method: {TestMethod}, Latency: {Latency}ms, " &
                   $"Local IP: {LocalIP}, Public IP: {PublicIP}, Time: {Timestamp}"
        End Function
    End Class
End Module

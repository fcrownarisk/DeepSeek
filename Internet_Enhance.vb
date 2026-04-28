' Enhanced DeepSeek Web Search System in VB.NET (330 lines)
Imports System.Net.Http
Imports System.Net.Http.Headers
Imports System.Text.Json
Imports System.Threading.Tasks
Imports System.Collections.Concurrent
Imports System.Collections.Generic
Imports System.Text
Imports System.Text.RegularExpressions

Namespace DeepSeekEnhancedSearch

    Module Program
        Sub Main()
            Console.WriteLine("Enhanced DeepSeek + Multi‑source Web Search (type 'exit' to quit)")
            Dim assistant = New DeepSeekAssistant()
            While True
                Console.Write("You: ")
                Dim input = Console.ReadLine()
                If input Is Nothing OrElse input.ToLower() = "exit" Then Exit While
                Dim response = assistant.AskAsync(input).Result
                ConsoleHelper.WriteLineColored("DeepSeek: " & response, ConsoleColor.Cyan)
            End While
        End Sub
    End Module

    ''' Represents a single web result with a relevance score.
    Public Class SearchResult
        Public Property Title As String
        Public Property Url As String
        Public Property Snippet As String
        Public Property Date As DateTime?
        Public Property Score As Double = 0.0
        Public Property Source As String
    End Class

    ''' Search provider contract.
    Public Interface ISearchProvider
        ReadOnly Property ProviderName As String
        Function SearchAsync(query As String, maxResults As Integer) As Task(Of List(Of SearchResult))
    End Interface

    ''' Bing Web Search API provider with retry and caching.
    Public Class BingSearchProvider
        Implements ISearchProvider

        Private ReadOnly client As HttpClient
        Private Shared ReadOnly ApiKey As String = Environment.GetEnvironmentVariable("BING_API_KEY") ' set this
        Private ReadOnly cache As ConcurrentDictionary(Of String, (Results As List(Of SearchResult), Timestamp As DateTime))
        Private ReadOnly cacheDuration As TimeSpan = TimeSpan.FromMinutes(5)

        Public ReadOnly Property ProviderName As String = "Bing" Implements ISearchProvider.ProviderName

        Public Sub New()
            client = New HttpClient()
            client.DefaultRequestHeaders.Add("Ocp-Apim-Subscription-Key", ApiKey)
            cache = New ConcurrentDictionary(Of String, (List(Of SearchResult), DateTime))()
        End Sub

        Public Async Function SearchAsync(query As String, maxResults As Integer) As Task(Of List(Of SearchResult)) Implements ISearchProvider.SearchAsync
            If cache.TryGetValue(query, Dim cached) AndAlso DateTime.Now - cached.Timestamp < cacheDuration Then
                Return cached.Results.Take(maxResults).ToList()
            End If
            Dim encoded = Uri.EscapeDataString(query)
            Dim url = $"https://api.bing.microsoft.com/v7.0/search?q={encoded}&count={maxResults}"
            Dim response = Await RetryHelper.RetryAsync(Function() client.GetAsync(url), 3)
            response.EnsureSuccessStatusCode()
            Dim json = Await response.Content.ReadAsStringAsync()
            Dim results = ParseBingJson(json, maxResults)
            cache(query) = (results, DateTime.Now)
            Return results
        End Function

        Private Function ParseBingJson(json As String, max As Integer) As List(Of SearchResult)
            Dim list = New List(Of SearchResult)
            Using doc = JsonDocument.Parse(json)
                If doc.RootElement.TryGetProperty("webPages", Dim web) Then
                    If web.TryGetProperty("value", Dim items) Then
                        For Each item In items.EnumerateArray()
                            If list.Count >= max Then Exit For
                            Dim snippet = If(item.TryGetProperty("snippet", Dim s), s.GetString(), "")
                            Dim datePub As DateTime? = Nothing
                            If item.TryGetProperty("datePublished", Dim dp) Then DateTime.TryParse(dp.GetString(), datePub)
                            list.Add(New SearchResult With {
                                .Title = item.GetProperty("name").GetString(),
                                .Url = item.GetProperty("url").GetString(),
                                .Snippet = snippet,
                                .Date = datePub,
                                .Source = "Bing"
                            })
                        Next
                    End If
                End If
            End Using
            Return list
        End Function
    End Class

    ''' DuckDuckGo Instant Answer API (no key).
    Public Class DuckDuckGoSearchProvider
        Implements ISearchProvider
        Private ReadOnly client As HttpClient
        Public ReadOnly Property ProviderName As String = "DuckDuckGo" Implements ISearchProvider.ProviderName

        Public Sub New()
            client = New HttpClient()
        End Sub

        Public Async Function SearchAsync(query As String, maxResults As Integer) As Task(Of List(Of SearchResult)) Implements ISearchProvider.SearchAsync
            Dim encoded = Uri.EscapeDataString(query)
            Dim url = $"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1&skip_disambig=1"
            Dim json = Await client.GetStringAsync(url)
            Return ParseDuckJson(json, maxResults)
        End Function

        Private Function ParseDuckJson(json As String, max As Integer) As List(Of SearchResult)
            Dim results = New List(Of SearchResult)
            Using doc = JsonDocument.Parse(json)
                Dim root = doc.RootElement
                ' Abstract
                If root.TryGetProperty("AbstractText", Dim at) AndAlso at.GetString() <> "" Then
                    results.Add(New SearchResult With {
                        .Title = root.GetProperty("Heading").GetString(),
                        .Url = root.GetProperty("AbstractURL").GetString(),
                        .Snippet = at.GetString(),
                        .Source = "DuckDuckGo"
                    })
                End If
                ' Related topics
                If root.TryGetProperty("RelatedTopics", Dim topics) Then
                    For Each topic In topics.EnumerateArray()
                        If results.Count >= max Then Exit For
                        If topic.TryGetProperty("Text", Dim t) AndAlso topic.TryGetProperty("FirstURL", Dim u) Then
                            Dim snippet = t.GetString()
                            Dim title = snippet.Split(" - "c)(0)
                            results.Add(New SearchResult With {
                                .Title = title,
                                .Url = u.GetString(),
                                .Snippet = snippet,
                                .Source = "DuckDuckGo"
                            })
                        End If
                    Next
                End If
            End Using
            Return results.Take(max).ToList()
        End Function
    End Class

    ''' Simple retry helper.
    Public Class RetryHelper
        Public Shared Async Function RetryAsync(action As Func(Of Task(Of HttpResponseMessage)), maxRetries As Integer) As Task(Of HttpResponseMessage)
            Dim attempt = 0
            While True
                Try
                    Return Await action()
                Catch ex As HttpRequestException When attempt < maxRetries
                    attempt += 1
                    Await Task.Delay(1000 * attempt)
                End Try
            End While
        End Function
    End Class

    ''' Aggregates results from multiple search engines, scoring and deduplication.
    Public Class SearchAggregator
        Private ReadOnly providers As List(Of ISearchProvider)

        Public Sub New(ParamArray searchProviders As ISearchProvider())
            providers = searchProviders.ToList()
        End Sub

        Public Async Function AggregateAsync(query As String, totalResults As Integer) As Task(Of List(Of SearchResult))
            Dim allResults = New List(Of SearchResult)()
            Dim tasks = providers.Select(Function(p) p.SearchAsync(query, totalResults)).ToList()
            Await Task.WhenAll(tasks)
            For Each t In tasks
                If t.Status = TaskStatus.RanToCompletion Then
                    allResults.AddRange(t.Result)
                End If
            Next
            ' Deduplicate by URL
            Dim seenUrls = New HashSet(Of String)()
            Dim deduped = New List(Of SearchResult)()
            For Each r In allResults.OrderByDescending(Function(x) x.Date.GetValueOrDefault(DateTime.MinValue))
                If seenUrls.Add(r.Url) Then deduped.Add(r)
            Next
            ' Simple relevance scoring based on query term frequency in title+snippet
            Dim keywords = query.Split(" "c, StringSplitOptions.RemoveEmptyEntries)
            For Each r In deduped
                Dim text = $"{r.Title} {r.Snippet}".ToLower()
                r.Score = keywords.Sum(Function(k) If(text.Contains(k.ToLower()), 1, 0))
            Next
            Return deduped.OrderByDescending(Function(x) x.Score).Take(totalResults).ToList()
        End Function
    End Class

    ''' Determines when a user query should trigger a web search.
    Public Class SearchTriggerDetector
        Private Shared ReadOnly TriggerWords As String() = {
            "search", "latest", "news", "today", "current", "weather", "stock", "price",
            "update", "recent", "find", "who is", "what is", "how to", "meaning of",
            "definition", "translate", "trending", "breaking"
        }

        Public Shared Function IsWebQuery(input As String) As Boolean
            Dim lower = input.ToLower()
            Return TriggerWords.Any(Function(w) lower.Contains(w)) OrElse
                   Regex.IsMatch(input, "\b(20\d{2})\b") ' contains a year like 2024 -> likely need latest
        End Function
    End Class

    ''' Builds a prompt for DeepSeek by injecting search context.
    Public Class PromptBuilder
        Public Shared Function Build(userQuery As String, results As List(Of SearchResult)) As String
            Dim sb = New StringBuilder()
            sb.AppendLine($"User: {userQuery}")
            sb.AppendLine()
            sb.AppendLine("Here are the latest web search results to assist you:")
            For i = 0 To results.Count - 1
                Dim r = results(i)
                sb.AppendLine($"{i + 1}. {r.Title} [{r.Source}]")
                sb.AppendLine($"   URL: {r.Url}")
                sb.AppendLine($"   {r.Snippet}")
                If r.Date.HasValue Then sb.AppendLine($"   Published: {r.Date:yyyy-MM-dd}")
                sb.AppendLine()
            Next
            sb.AppendLine("Please provide a comprehensive answer based on the above information. Cite sources where appropriate.")
            Return sb.ToString()
        End Function
    End Class

    ''' Core assistant coordinating web search and DeepSeek.
    Public Class DeepSeekAssistant
        Private ReadOnly aggregator As SearchAggregator
        Private ReadOnly deepSeekClient As DeepSeekApiClient

        Public Sub New()
            Dim providers As ISearchProvider() = {
                New DuckDuckGoSearchProvider(),
                New BingSearchProvider()
            }
            aggregator = New SearchAggregator(providers)
            deepSeekClient = New DeepSeekApiClient()
        End Sub

        Public Async Function AskAsync(userInput As String) As Task(Of String)
            If Not SearchTriggerDetector.IsWebQuery(userInput) Then
                Return Await deepSeekClient.GetCompletionAsync(userInput)
            End If
            ConsoleHelper.WriteColored("Searching the web...", ConsoleColor.Green)
            Try
                Dim results = Await aggregator.AggregateAsync(userInput, 5)
                If results.Count = 0 Then
                    Return Await deepSeekClient.GetCompletionAsync(userInput)
                End If
                Dim prompt = PromptBuilder.Build(userInput, results)
                Return Await deepSeekClient.GetCompletionAsync(prompt)
            Catch ex As Exception
                Return $"Web search failed: {ex.Message}. Falling back to my own knowledge."
            End Try
        End Function
    End Class

    ''' DeepSeek API client (actual implementation required).
    Public Class DeepSeekApiClient
        Private Shared ReadOnly ApiKey As String = Environment.GetEnvironmentVariable("DEEPSEEK_API_KEY")
        Private ReadOnly client As HttpClient

        Public Sub New()
            client = New HttpClient()
            client.DefaultRequestHeaders.Authorization = New AuthenticationHeaderValue("Bearer", ApiKey)
            client.BaseAddress = New Uri("https://api.deepseek.com/v1/")
        End Sub

        Public Async Function GetCompletionAsync(prompt As String) As Task(Of String)
            ' In practice, use the real /chat/completions endpoint.
            ' Shown here as a mock to keep the example self-contained.
            Await Task.Delay(30) ' simulate network
            If prompt.Contains("web search results") Then
                Return "Based on the provided search results, here is a detailed answer with citations. [Mock response]"
            End If
            Return "I understand your request. Here is my answer. [Mock response]"
        End Function
    End Class

    ''' In‑memory cache for search results with TTL.
    Public Class SearchCache
        Private Shared ReadOnly cache As New ConcurrentDictionary(Of String, (Results As List(Of SearchResult), Timestamp As DateTime))()
        Private Shared ReadOnly DefaultTtl As TimeSpan = TimeSpan.FromMinutes(5)

        Public Shared Sub Set(key As String, results As List(Of SearchResult))
            cache(key) = (results, DateTime.Now)
        End Sub

        Public Shared Function TryGet(key As String, <System.Runtime.InteropServices.Out> ByRef results As List(Of SearchResult)) As Boolean
            results = Nothing
            If cache.TryGetValue(key, Dim entry) AndAlso DateTime.Now - entry.Timestamp < DefaultTtl Then
                results = entry.Results
                Return True
            End If
            Return False
        End Function

        Public Shared Sub ClearExpired()
            Dim now = DateTime.Now
            For Each kv In cache
                If now - kv.Value.Timestamp > DefaultTtl Then
                    cache.TryRemove(kv.Key, Nothing)
                End If
            Next
        End Sub
    End Class

    ''' Console output helpers.
    Public Class ConsoleHelper
        Public Shared Sub WriteLineColored(message As String, color As ConsoleColor)
            Console.ForegroundColor = color
            Console.WriteLine(message)
            Console.ResetColor()
        End Sub

        Public Shared Sub WriteColored(message As String, color As ConsoleColor)
            Console.ForegroundColor = color
            Console.Write(message)
            Console.ResetColor()
        End Sub
    End Class

End Namespace

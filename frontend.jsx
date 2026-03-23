import React, { useState, useEffect, useCallback } from 'react';
import { Download, Send, CheckCircle, AlertCircle, Loader, FileText, BarChart3 } from 'lucide-react';

const API_BASE_URL = 'http://localhost:8000';

export default function ResearchAssistant() {
  const [topic, setTopic] = useState('');
  const [sessionId, setSessionId] = useState('');
  const [status, setStatus] = useState('idle');
  const [phase, setPhase] = useState('');
  const [draftReady, setDraftReady] = useState(false);
  const [finalReady, setFinalReady] = useState(false);
  const [draftMarkdown, setDraftMarkdown] = useState('');
  const [error, setError] = useState('');
  const [reviewScore, setReviewScore] = useState(null);
  const [autoApprove, setAutoApprove] = useState(false);
  const [showDraft, setShowDraft] = useState(false);

  // Start research
  const startResearch = async (e) => {
    e.preventDefault();
    if (!topic.trim()) {
      setError('Please enter a research topic');
      return;
    }

    setError('');
    setStatus('researching');
    setPhase('Initializing research...');
    setDraftReady(false);
    setFinalReady(false);

    try {
      const response = await fetch(`${API_BASE_URL}/research/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic, auto_approve: autoApprove })
      });

      const data = await response.json();
      setSessionId(data.session_id);

      // Start polling for status
      pollStatus(data.session_id);
    } catch (err) {
      setError(`Failed to start research: ${err.message}`);
      setStatus('idle');
    }
  };

  // Poll research status
  const pollStatus = useCallback(async (sid) => {
    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/research/status/${sid}`);
        const data = await response.json();

        setPhase(data.status);

        if (data.research_complete && !data.analysis_complete) {
          setPhase('🔍 Researching... Complete! Moving to analysis...');
        } else if (data.analysis_complete && !data.draft_ready) {
          setPhase('📊 Analyzing... Complete! Generating draft...');
        } else if (data.draft_ready && !autoApprove && !data.final_ready) {
          setPhase('✍️ Draft Report Ready - Awaiting Your Approval');
          setDraftReady(true);
          // Fetch draft
          const draftResp = await fetch(`${API_BASE_URL}/research/draft/${sid}`);
          const draftData = await draftResp.json();
          setDraftMarkdown(draftData.markdown);
        } else if (data.final_ready) {
          setPhase('✅ Report Complete!');
          setStatus('complete');
          setFinalReady(true);
          if (data.review_score) {
            setReviewScore(data.review_score);
          }
          clearInterval(pollInterval);
        } else if (data.error) {
          setError(data.error);
          setStatus('error');
          clearInterval(pollInterval);
        }
      } catch (err) {
        console.error('Poll error:', err);
      }
    }, 3000);
  }, [autoApprove]);

  // Approve draft
  const approveDraft = async () => {
    try {
      await fetch(`${API_BASE_URL}/research/approve/${sessionId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approved: true })
      });

      setDraftReady(false);
      setPhase('🔍 Proceeding to critique phase...');
      pollStatus(sessionId);
    } catch (err) {
      setError(`Failed to approve: ${err.message}`);
    }
  };

  // Download report
  const downloadReport = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/research/download/${sessionId}`);
      const blob = await response.blob();
      
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `research_report_${sessionId}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      setError(`Failed to download: ${err.message}`);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8 mt-4">
          <div className="flex items-center justify-center gap-3 mb-3">
            <BarChart3 className="w-10 h-10 text-indigo-600" />
            <h1 className="text-4xl font-bold text-gray-800">Research Assistant</h1>
          </div>
          <p className="text-gray-600 text-lg">AI-powered multi-agent research system</p>
        </div>

        {/* Main Card */}
        <div className="bg-white rounded-lg shadow-lg p-8 mb-6">
          {/* Input Form */}
          {status === 'idle' && (
            <form onSubmit={startResearch} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Research Topic
                </label>
                <textarea
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  placeholder="Enter your research topic (e.g., 'Impact of AI on healthcare', 'Climate change solutions')"
                  className="w-full h-24 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none"
                />
              </div>

              <div className="flex items-center gap-3 bg-blue-50 p-4 rounded-lg">
                <input
                  type="checkbox"
                  id="autoApprove"
                  checked={autoApprove}
                  onChange={(e) => setAutoApprove(e.target.checked)}
                  className="w-4 h-4 text-indigo-600"
                />
                <label htmlFor="autoApprove" className="text-sm text-gray-700">
                  Auto-approve draft (skip manual review step)
                </label>
              </div>

              <button
                type="submit"
                className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-3 rounded-lg flex items-center justify-center gap-2 transition"
              >
                <Send className="w-5 h-5" />
                Start Research
              </button>
            </form>
          )}

          {/* Status Display */}
          {status !== 'idle' && (
            <div className="space-y-6">
              {/* Topic Display */}
              <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                <p className="text-sm text-gray-600">Research Topic</p>
                <p className="text-xl font-semibold text-gray-800">{topic}</p>
              </div>

              {/* Phase Progress */}
              <div className="bg-blue-50 p-6 rounded-lg border-l-4 border-blue-500">
                <div className="flex items-start gap-3">
                  {status === 'error' ? (
                    <AlertCircle className="w-6 h-6 text-red-500 flex-shrink-0 mt-1" />
                  ) : status === 'complete' ? (
                    <CheckCircle className="w-6 h-6 text-green-500 flex-shrink-0 mt-1" />
                  ) : (
                    <Loader className="w-6 h-6 text-indigo-600 flex-shrink-0 mt-1 animate-spin" />
                  )}
                  <div className="flex-1">
                    <p className="font-semibold text-gray-800">{phase}</p>
                    <p className="text-sm text-gray-600 mt-1">
                      {status === 'researching' && 'Gathering and analyzing information...'}
                      {status === 'complete' && 'Your research report is ready!'}
                      {status === 'error' && 'An error occurred during processing.'}
                    </p>
                  </div>
                </div>
              </div>

              {/* Error Message */}
              {error && (
                <div className="bg-red-50 p-4 rounded-lg border border-red-200">
                  <p className="text-red-800 font-semibold">Error</p>
                  <p className="text-red-700 text-sm mt-1">{error}</p>
                </div>
              )}

              {/* Draft Approval Section */}
              {draftReady && (
                <div className="bg-yellow-50 p-6 rounded-lg border-2 border-yellow-300">
                  <div className="flex items-center gap-2 mb-4">
                    <FileText className="w-5 h-5 text-yellow-600" />
                    <h3 className="font-semibold text-yellow-900">Draft Report Ready</h3>
                  </div>
                  
                  {!showDraft ? (
                    <button
                      onClick={() => setShowDraft(true)}
                      className="text-indigo-600 underline text-sm mb-4"
                    >
                      Preview draft report
                    </button>
                  ) : (
                    <div className="bg-white p-4 rounded max-h-96 overflow-y-auto text-sm mb-4 border border-yellow-200">
                      <div className="whitespace-pre-wrap text-gray-700 font-mono text-xs">
                        {draftMarkdown}
                      </div>
                    </div>
                  )}

                  <div className="flex gap-3">
                    <button
                      onClick={approveDraft}
                      className="flex-1 bg-green-600 hover:bg-green-700 text-white font-semibold py-2 rounded-lg transition"
                    >
                      ✅ Approve & Continue
                    </button>
                  </div>
                </div>
              )}

              {/* Review Score */}
              {reviewScore !== null && (
                <div className="bg-purple-50 p-4 rounded-lg border border-purple-200">
                  <p className="text-sm text-gray-600">Quality Review Score</p>
                  <div className="flex items-center gap-2 mt-2">
                    <div className="flex-1 bg-gray-200 rounded-full h-3 overflow-hidden">
                      <div
                        className={`h-full transition-all ${
                          reviewScore >= 80 ? 'bg-green-500' :
                          reviewScore >= 60 ? 'bg-yellow-500' :
                          'bg-orange-500'
                        }`}
                        style={{ width: `${reviewScore}%` }}
                      />
                    </div>
                    <span className="font-semibold text-gray-800">{reviewScore}/100</span>
                  </div>
                </div>
              )}

              {/* Download Button */}
              {finalReady && (
                <button
                  onClick={downloadReport}
                  className="w-full bg-green-600 hover:bg-green-700 text-white font-semibold py-3 rounded-lg flex items-center justify-center gap-2 transition"
                >
                  <Download className="w-5 h-5" />
                  Download Report as PDF
                </button>
              )}

              {/* Reset Button */}
              {status === 'complete' || status === 'error' ? (
                <button
                  onClick={() => {
                    setStatus('idle');
                    setTopic('');
                    setSessionId('');
                    setError('');
                    setDraftReady(false);
                    setFinalReady(false);
                    setShowDraft(false);
                  }}
                  className="w-full bg-gray-300 hover:bg-gray-400 text-gray-800 font-semibold py-2 rounded-lg transition"
                >
                  Start New Research
                </button>
              ) : null}
            </div>
          )}
        </div>

        {/* Info Footer */}
        <div className="bg-indigo-50 rounded-lg p-4 border border-indigo-200 text-center text-sm text-gray-700">
          <p>
            This research system uses multiple AI agents to search, analyze, and write comprehensive reports.
            All processing happens with human-in-the-loop approval gates.
          </p>
        </div>
      </div>
    </div>
  );
}
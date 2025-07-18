import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useLocation, useNavigate } from "react-router-dom";
import { FileText, Download, Eye, ArrowLeft, File, RefreshCw, AlertCircle } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { useState, useEffect, useRef } from "react";
import { fetchWithAuth } from "@/lib/api";
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';

const Preview = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { toast } = useToast();
  const docId = new URLSearchParams(window.location.search).get("id");
  const [downloading, setDownloading] = useState<{pdf?: boolean; docx?: boolean}>({});
  const [docMeta, setDocMeta] = useState<any>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [exportErrors, setExportErrors] = useState<{pdf?: string; docx?: string}>({});
  const [retryAttempts, setRetryAttempts] = useState<{pdf?: number; docx?: number}>({});
  const errorTimeout = useRef<NodeJS.Timeout | null>(null);

  const editor = useEditor({
    extensions: [StarterKit],
    content: "",
    editable: true,
  });

  useEffect(() => {
    if (!docId) {
      setErrorMsg("No document ID found. Redirecting to dashboard...");
      errorTimeout.current = setTimeout(() => navigate("/dashboard"), 3000);
      return;
    }
    const fetchDoc = async () => {
      setLoading(true);
      setErrorMsg(null);
      try {
        const res = await fetchWithAuth(`/session/${docId}`);
        if (!res.ok) {
          if (res.status === 404) {
            throw new Error("Document not found");
          } else if (res.status === 401) {
            throw new Error("Authentication required. Please log in again.");
          } else {
            throw new Error(`Failed to load document (${res.status})`);
          }
        }
        const data = await res.json();
        setDocMeta(data);
        if (editor) {
          editor.commands.setContent(data.ai_content || "<p>Start editing your document here...</p>");
        }
      } catch (err: any) {
        console.error("Error loading document:", err);
        setErrorMsg(`Error loading document: ${err.message}. Redirecting to dashboard...`);
        errorTimeout.current = setTimeout(() => navigate("/dashboard"), 3000);
      } finally {
        setLoading(false);
      }
    };
    fetchDoc();
    return () => {
      if (errorTimeout.current) clearTimeout(errorTimeout.current);
    };
    // eslint-disable-next-line
  }, [docId, editor]);

  const getSpecificErrorMessage = (error: any, format: string): string => {
    const message = error.message || error.detail || "Unknown error";
    
    // Handle specific error types
    if (message.includes("pdf_generation_failed")) {
      return "PDF generation failed. The document content may contain unsupported formatting.";
    }
    if (message.includes("html_parsing_error")) {
      return "Document content could not be processed. Please check for invalid formatting.";
    }
    if (message.includes("file_upload_failed")) {
      return "Generated file could not be saved. Please try again.";
    }
    if (message.includes("storage_quota")) {
      return "Storage limit reached. Please contact support or try again later.";
    }
    if (message.includes("timeout")) {
      return "Export timed out. Large documents may take longer to process.";
    }
    if (message.includes("401") || message.includes("unauthorized")) {
      return "Authentication expired. Please refresh the page and try again.";
    }
    if (message.includes("404")) {
      return "Document not found. It may have been deleted.";
    }
    if (message.includes("500")) {
      return "Server error occurred during export. Please try again.";
    }
    
    return `${format.toUpperCase()} export failed: ${message}`;
  };

  const handleExport = async (format: "pdf" | "docx", isRetry: boolean = false) => {
    if (!docId) {
      toast({
        title: "Export failed",
        description: "No document ID found",
        variant: "destructive",
      });
      return;
    }

    // Clear previous errors for this format
    setExportErrors((prev) => ({ ...prev, [format]: undefined }));
    setDownloading((prev) => ({ ...prev, [format]: true }));
    
    const currentAttempt = (retryAttempts[format] || 0) + 1;
    const maxRetries = 3;
    
    // Show appropriate toast message
    if (isRetry) {
      toast({
        title: `Retrying export (${currentAttempt}/${maxRetries})`,
        description: `Attempting to export as ${format.toUpperCase()} again...`,
      });
    } else {
      toast({
        title: `Export started`,
        description: `Your document is being exported as ${format.toUpperCase()}...`,
      });
    }
    
    try {
      const res = await fetchWithAuth(`/export/${format}/${docId}`, { 
        method: "POST",
        // Add timeout for better error handling
        signal: AbortSignal.timeout(60000) // 60 second timeout
      });
      
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        const errorMessage = errorData.detail || errorData.message || `Export failed with status ${res.status}`;
        throw new Error(errorMessage);
      }
      
      const data = await res.json();
      
      if (!data.url) {
        throw new Error("No file URL returned from server");
      }

      // Validate that the URL is actually a PDF for PDF exports
      if (format === "pdf" && data.url && !data.url.includes('.pdf')) {
        console.warn("PDF export may have returned non-PDF URL:", data.url);
      }
      
      // Success - reset retry attempts and clear errors
      setRetryAttempts((prev) => ({ ...prev, [format]: 0 }));
      setExportErrors((prev) => ({ ...prev, [format]: undefined }));
      
      // For PDF files, use the direct download URL if available
      if (format === "pdf") {
        // Check if we have a direct download URL from the backend
        if (data.direct_download_url) {
          // Use the direct download URL which will force download with proper headers
          const baseUrl = window.location.origin;
          const apiUrl = `${baseUrl}/api${data.direct_download_url}`;
          
          // Open the direct download URL in a new tab
          window.open(apiUrl, "_blank");
          
          toast({
            title: `PDF Export Successful`,
            description: `Your PDF download has started. If it doesn't begin automatically, use the download button.`,
            action: (
              <Button 
                size="sm" 
                onClick={() => window.open(apiUrl, "_blank")}
                className="ml-2"
              >
                Download
              </Button>
            ),
          });
        } else {
          // Fallback to the blob approach if direct_download_url is not available
          // Add a timestamp to the URL to prevent caching issues
          const timestampedUrl = `${data.url}${data.url.includes('?') ? '&' : '?'}t=${Date.now()}`;
          
          // Create a blob from the URL to force download
          fetch(timestampedUrl)
            .then(response => response.blob())
            .then(blob => {
              // Create a blob URL
              const blobUrl = URL.createObjectURL(blob);
              
              // Create a download link
              const link = document.createElement('a');
              link.href = blobUrl;
              link.download = data.filename || `document-${Date.now()}.pdf`;
              link.style.display = 'none';
              
              // Append to body, click, and remove
              document.body.appendChild(link);
              link.click();
              
              // Clean up
              setTimeout(() => {
                document.body.removeChild(link);
                URL.revokeObjectURL(blobUrl);
              }, 100);
            })
            .catch(err => {
              console.error("Error downloading PDF:", err);
              // Fallback to direct URL if fetch fails
              window.location.href = timestampedUrl;
            });
          
          toast({
            title: `PDF Export Successful`,
            description: `Your PDF download has started. If it doesn't begin automatically, use the download button.`,
            action: (
              <Button 
                size="sm" 
                onClick={() => {
                  // Create a new download link for the button
                  fetch(timestampedUrl)
                    .then(response => response.blob())
                    .then(blob => {
                      const blobUrl = URL.createObjectURL(blob);
                      const link = document.createElement('a');
                      link.href = blobUrl;
                      link.download = data.filename || `document-${Date.now()}.pdf`;
                      link.click();
                      setTimeout(() => URL.revokeObjectURL(blobUrl), 100);
                    })
                    .catch(() => window.location.href = timestampedUrl);
                }}
                className="ml-2"
              >
                Download
              </Button>
            ),
          });
        }
      } else {
        // For non-PDF formats, use the original approach
        const newWindow = window.open(data.url, "_blank");
        
        // Check if popup was blocked
        if (!newWindow || newWindow.closed || typeof newWindow.closed === "undefined") {
          toast({
            title: `Export completed`,
            description: `${format.toUpperCase()} ready! Click here to download.`,
            action: (
              <Button 
                size="sm" 
                onClick={() => window.open(data.url, "_blank")}
                className="ml-2"
              >
                Download
              </Button>
            ),
          });
        } else {
          toast({
            title: `Export completed`,
            description: data.message || `Document exported successfully as ${format.toUpperCase()}.`,
          });
        }
      }
      
    } catch (err: any) {
      console.error("Export error:", err);
      
      const specificError = getSpecificErrorMessage(err, format);
      setExportErrors((prev) => ({ ...prev, [format]: specificError }));
      setRetryAttempts((prev) => ({ ...prev, [format]: currentAttempt }));
      
      // Show error toast with retry option if we haven't exceeded max retries
      if (currentAttempt < maxRetries && !err.name?.includes("AbortError")) {
        toast({
          title: "Export failed",
          description: specificError,
          variant: "destructive",
          action: (
            <Button 
              size="sm" 
              variant="outline" 
              onClick={() => handleExport(format, true)}
              className="ml-2"
            >
              <RefreshCw className="h-3 w-3 mr-1" />
              Retry
            </Button>
          ),
        });
      } else {
        // Final failure - no more retries
        toast({
          title: "Export failed",
          description: currentAttempt >= maxRetries 
            ? `${specificError} Maximum retry attempts reached.`
            : specificError,
          variant: "destructive",
        });
      }
    } finally {
      setDownloading((prev) => ({ ...prev, [format]: false }));
    }
  };

  const handleSave = async () => {
    if (!docId || !editor) return;
    setSaving(true);
    setSaveSuccess(false);
    try {
      const res = await fetchWithAuth("/save-edits", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: docId, content: editor.getHTML() }),
      });
      if (!res.ok) throw new Error("Failed to save edits");
      toast({ title: "Edits saved", description: "Your changes have been saved." });
      setSaveSuccess(true);
    } catch (err: any) {
      toast({ title: "Save failed", description: err.message, variant: "destructive" });
    } finally {
      setSaving(false);
    }
  };

  const goBack = () => {
    navigate("/dashboard");
  };

  if (errorMsg) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen">
        <div className="bg-red-100 text-red-700 px-6 py-4 rounded shadow">
          {errorMsg}
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mb-4"></div>
        <p className="text-muted-foreground">Loading document...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-background to-secondary/20">
      <header className="border-b bg-card/50 backdrop-blur-sm">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <Button variant="ghost" size="sm" onClick={goBack} className="mr-2">
              <ArrowLeft className="h-4 w-4" />
            </Button>
            <div className="bg-primary rounded-full p-2">
              <FileText className="h-5 w-5 text-primary-foreground" />
            </div>
            <h1 className="text-xl font-bold">DocGen</h1>
          </div>
          <div className="flex items-center space-x-2">
            <Button onClick={handleSave} disabled={saving || !editor} className="flex items-center space-x-2">
              {saving ? "Saving..." : saveSuccess ? "Saved" : "Save"}
            </Button>
            <Button 
              variant={exportErrors.pdf ? "destructive" : "outline"} 
              onClick={() => handleExport("pdf")} 
              className="flex items-center space-x-2" 
              disabled={downloading.pdf}
            >
              {downloading.pdf ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current" />
                  <span>Exporting...</span>
                </>
              ) : exportErrors.pdf ? (
                <>
                  <AlertCircle className="h-4 w-4" />
                  <span>Failed</span>
                </>
              ) : (
                <>
                  <Download className="h-4 w-4" />
                  <span>PDF</span>
                </>
              )}
            </Button>
            <Button 
              variant={exportErrors.docx ? "destructive" : "default"}
              onClick={() => handleExport("docx")} 
              className="flex items-center space-x-2" 
              disabled={downloading.docx}
            >
              {downloading.docx ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current" />
                  <span>Exporting...</span>
                </>
              ) : exportErrors.docx ? (
                <>
                  <AlertCircle className="h-4 w-4" />
                  <span>Failed</span>
                </>
              ) : (
                <>
                  <Download className="h-4 w-4" />
                  <span>DOCX</span>
                </>
              )}
            </Button>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto animate-fade-in">
          <div className="text-center mb-8">
            <h2 className="text-3xl font-bold mb-2">Document Preview</h2>
            <p className="text-muted-foreground">Review your generated document before exporting</p>
          </div>

          <div className="grid gap-8 lg:grid-cols-3">
            {/* Document Info Sidebar */}
            <div className="lg:col-span-1">
              <Card className="shadow-medium border-0">
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <Eye className="h-5 w-5 text-primary" />
                    <span>Document Info</span>
                  </CardTitle>
                  <CardDescription>Generated document details</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <Label className="text-sm font-medium text-muted-foreground">Title</Label>
                    <p className="text-sm font-medium">{docMeta.documentTitle || "Untitled Document"}</p>
                  </div>
                  <div>
                    <Label className="text-sm font-medium text-muted-foreground">Type</Label>
                    <p className="text-sm">{docMeta.documentType || "Unknown Type"}</p>
                  </div>
                  <div>
                    <Label className="text-sm font-medium text-muted-foreground">Source File</Label>
                    <p className="text-sm flex items-center space-x-1">
                      <File className="h-3 w-3" />
                      <span>{docMeta.fileName || "No file"}</span>
                    </p>
                  </div>
                  <div>
                    <Label className="text-sm font-medium text-muted-foreground">Prompt</Label>
                    <p className="text-sm text-muted-foreground">{docMeta.prompt || "No prompt provided"}</p>
                  </div>
                </CardContent>
              </Card>

              <Card className="shadow-medium border-0 mt-4">
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <Download className="h-5 w-5 text-primary" />
                    <span>Export Options</span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="space-y-2">
                    <Button 
                      variant={exportErrors.pdf ? "destructive" : "outline"}
                      onClick={() => handleExport("pdf")}
                      className="w-full justify-start"
                      disabled={downloading.pdf}
                    >
                      {downloading.pdf ? (
                        <>
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current mr-2" />
                          Exporting...
                        </>
                      ) : exportErrors.pdf ? (
                        <>
                          <AlertCircle className="h-4 w-4 mr-2" />
                          Export Failed
                        </>
                      ) : (
                        <>
                          <Download className="h-4 w-4 mr-2" />
                          Export as PDF
                        </>
                      )}
                    </Button>
                    {exportErrors.pdf && (
                      <div className="text-xs text-destructive px-2 py-1 bg-destructive/10 rounded">
                        {exportErrors.pdf}
                        {(retryAttempts.pdf || 0) < 3 && (
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleExport("pdf", true)}
                            className="ml-2 h-6 px-2 text-xs"
                          >
                            <RefreshCw className="h-3 w-3 mr-1" />
                            Retry
                          </Button>
                        )}
                      </div>
                    )}
                  </div>
                  
                  <div className="space-y-2">
                    <Button 
                      variant={exportErrors.docx ? "destructive" : "default"}
                      onClick={() => handleExport("docx")}
                      className="w-full justify-start"
                      disabled={downloading.docx}
                    >
                      {downloading.docx ? (
                        <>
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current mr-2" />
                          Exporting...
                        </>
                      ) : exportErrors.docx ? (
                        <>
                          <AlertCircle className="h-4 w-4 mr-2" />
                          Export Failed
                        </>
                      ) : (
                        <>
                          <Download className="h-4 w-4 mr-2" />
                          Export as DOCX
                        </>
                      )}
                    </Button>
                    {exportErrors.docx && (
                      <div className="text-xs text-destructive px-2 py-1 bg-destructive/10 rounded">
                        {exportErrors.docx}
                        {(retryAttempts.docx || 0) < 3 && (
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleExport("docx", true)}
                            className="ml-2 h-6 px-2 text-xs"
                          >
                            <RefreshCw className="h-3 w-3 mr-1" />
                            Retry
                          </Button>
                        )}
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Document Preview */}
            <div className="lg:col-span-2">
              <Card className="shadow-large border-0 min-h-[600px]">
                <CardHeader>
                  <CardTitle>Document Preview</CardTitle>
                  <CardDescription>Generated content based on your specifications</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="bg-background rounded-lg p-8 shadow-soft min-h-[500px] border">
                    <div className="space-y-6">
                      <div className="text-center border-b pb-4">
                        <h1 className="text-2xl font-bold">{docMeta.documentTitle || "Generated Document"}</h1>
                        <p className="text-muted-foreground">{docMeta.documentType || "Document Type"}</p>
                      </div>
                      <div className="space-y-4">
                        <EditorContent editor={editor} />
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

const Label = ({ children, className }: { children: React.ReactNode; className?: string }) => (
  <div className={className}>{children}</div>
);

export default Preview;
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useLocation, useNavigate } from "react-router-dom";
import { FileText, Download, Eye, ArrowLeft, File, RefreshCw, AlertCircle, Info, Save, Check } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { useState, useEffect, useRef, useCallback, lazy, Suspense } from "react";
import { fetchWithAuth } from "@/lib/api";
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import { Accordion, AccordionItem, AccordionTrigger, AccordionContent } from "@/components/ui/accordion";
import { TiptapTableExtension, LazyTableMenu } from "@/components/LazyTiptapTableExtension";
import ExportProgress from "@/components/ExportProgress";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { useDebouncedCallback } from "@/hooks/use-debounce";
import KeyboardShortcutsHelp from "@/components/KeyboardShortcutsHelp";
import "@/styles/tiptap-table.css";

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
  const [exportOperations, setExportOperations] = useState<{pdf?: string; docx?: string}>({});
  const [showExportProgress, setShowExportProgress] = useState<{pdf?: boolean; docx?: boolean}>({});
  const errorTimeout = useRef<NodeJS.Timeout | null>(null);

  // Initialize editor with auto-save functionality
  const editor = useEditor({
    extensions: [StarterKit, TiptapTableExtension],
    content: "",
    editable: true,
    onUpdate: ({ editor }) => {
      // Trigger auto-save when content changes
      debouncedSave();
    },
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
    
    // Show progress tracking UI
    setShowExportProgress((prev) => ({ ...prev, [format]: true }));
    
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
        const errorMessage = errorData.detail?.message || errorData.detail || errorData.message || `Export failed with status ${res.status}`;
        throw new Error(errorMessage);
      }
      
      const data = await res.json();
      
      if (!data.url) {
        throw new Error("No file URL returned from server");
      }

      // Store operation ID for progress tracking if available
      if (data.operation_id) {
        setExportOperations((prev) => ({ ...prev, [format]: data.operation_id }));
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
      
      // Hide progress tracking UI after successful export
      setTimeout(() => {
        setShowExportProgress((prev) => ({ ...prev, [format]: false }));
      }, 3000);
      
    } catch (err: any) {
      console.error("Export error:", err);
      
      // Try to extract detailed error information
      let errorDetail = err.message;
      try {
        // Check if the error message is JSON
        if (typeof err.message === 'string' && err.message.startsWith('{')) {
          const errorObj = JSON.parse(err.message);
          if (errorObj.detail && errorObj.detail.user_message) {
            errorDetail = errorObj.detail.user_message;
          } else if (errorObj.detail && errorObj.detail.message) {
            errorDetail = errorObj.detail.message;
          }
        }
      } catch (e) {
        // If parsing fails, use the original error message
      }
      
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
      
      // Keep progress tracking UI visible for errors
    } finally {
      setDownloading((prev) => ({ ...prev, [format]: false }));
    }
  };

  // Regular save function
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
      
      // Show success state for 2 seconds
      setTimeout(() => {
        setSaveSuccess(false);
      }, 2000);
    } catch (err: any) {
      toast({ title: "Save failed", description: err.message, variant: "destructive" });
    } finally {
      setSaving(false);
    }
  };
  
  // Debounced auto-save function
  const debouncedSave = useDebouncedCallback(async () => {
    if (!docId || !editor) return;
    
    try {
      setSaving(true);
      const res = await fetchWithAuth("/save-edits", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: docId, content: editor.getHTML() }),
      });
      
      if (!res.ok) throw new Error("Failed to auto-save");
      
      // Show subtle success indicator
      setSaveSuccess(true);
      
      // Hide success indicator after 2 seconds
      setTimeout(() => {
        setSaveSuccess(false);
      }, 2000);
    } catch (err: any) {
      console.error("Auto-save failed:", err);
      // Don't show toast for auto-save failures to avoid disrupting the user
    } finally {
      setSaving(false);
    }
  }, 2000); // 2 second debounce delay

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
            <Button 
              onClick={handleSave} 
              disabled={saving || !editor} 
              className="flex items-center space-x-2"
              variant={saveSuccess ? "default" : "outline"}
            >
              {saving ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current mr-1" />
                  <span>Saving...</span>
                </>
              ) : saveSuccess ? (
                <>
                  <Check className="h-4 w-4 mr-1 text-green-500" />
                  <span>Saved</span>
                </>
              ) : (
                <>
                  <Save className="h-4 w-4 mr-1" />
                  <span>Save</span>
                </>
              )}
            </Button>
            <KeyboardShortcutsHelp />
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

      <main className="container mx-auto px-4 py-8 max-w-none">
        <div className="w-full animate-fade-in">
          <div className="text-center mb-8">
            <h2 className="text-3xl font-bold mb-2">Document Preview</h2>
            <p className="text-muted-foreground">Review your generated document before exporting</p>
          </div>

          {/* Responsive layout: mobile stacked, tablet/desktop with sidebar */}
          <div className="flex flex-col xl:flex-row gap-6">
            {/* Document Preview - Main Content (80%+ width on large screens) */}
            <div className="flex-1 xl:w-4/5 order-2 xl:order-1">
              <Card className="shadow-large border-0 min-h-[600px]">
                <CardHeader className="pb-4">
                  <CardTitle className="text-lg">Document Preview</CardTitle>
                  <CardDescription>Generated content based on your specifications</CardDescription>
                </CardHeader>
                <CardContent className="p-0">
                  <div className="bg-background rounded-lg mx-6 mb-6 shadow-soft min-h-[500px] border">
                    <div className="p-8 lg:p-12 space-y-8">
                      <div className="text-center border-b pb-6">
                        <h1 className="text-3xl lg:text-4xl font-bold leading-tight mb-3">
                          {docMeta.documentTitle || "Generated Document"}
                        </h1>
                        <p className="text-muted-foreground text-lg">
                          {docMeta.documentType || "Document Type"}
                        </p>
                      </div>
                      <div className="max-w-none">
                        <LazyTableMenu editor={editor} />
                        <EditorContent 
                          editor={editor} 
                          className="tiptap-editor"
                        />
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Document Info Sidebar (20% width on large screens) */}
            <div className="xl:w-1/5 xl:min-w-[280px] xl:max-w-[320px] order-1 xl:order-2">
              <div className="space-y-4">
                <Card className="shadow-medium border-0">
                  <CardHeader className="pb-3">
                    <CardTitle className="flex items-center space-x-2 text-base">
                      <Eye className="h-4 w-4 text-primary" />
                      <span>Document Info</span>
                    </CardTitle>
                    <CardDescription className="text-sm">Generated document details</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3 text-sm">
                    <div>
                      <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Title</Label>
                      <p className="text-sm font-medium mt-1 leading-snug">{docMeta.documentTitle || "Untitled Document"}</p>
                    </div>
                    <div>
                      <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Type</Label>
                      <p className="text-sm mt-1">{docMeta.documentType || "Unknown Type"}</p>
                    </div>
                    <div>
                      <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Source File</Label>
                      <p className="text-sm flex items-center space-x-1 mt-1">
                        <File className="h-3 w-3 flex-shrink-0" />
                        <span className="truncate">{docMeta.fileName || "No file"}</span>
                      </p>
                    </div>
                    <div>
                      <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Prompt</Label>
                      <p className="text-sm text-muted-foreground mt-1 leading-snug line-clamp-3">
                        {docMeta.prompt || "No prompt provided"}
                      </p>
                    </div>
                  </CardContent>
                </Card>

                <Card className="shadow-medium border-0">
                  <CardHeader className="pb-3">
                    <CardTitle className="flex items-center space-x-2 text-base">
                      <Download className="h-4 w-4 text-primary" />
                      <span>Export Options</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="space-y-2">
                      <Button 
                        variant={exportErrors.pdf ? "destructive" : "outline"}
                        onClick={() => handleExport("pdf")}
                        className="w-full justify-start text-sm h-9"
                        disabled={downloading.pdf}
                      >
                        {downloading.pdf ? (
                          <>
                            <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-current mr-2" />
                            Exporting...
                          </>
                        ) : exportErrors.pdf ? (
                          <>
                            <AlertCircle className="h-3 w-3 mr-2" />
                            Export Failed
                          </>
                        ) : (
                          <>
                            <Download className="h-3 w-3 mr-2" />
                            Export as PDF
                          </>
                        )}
                      </Button>
                      {exportErrors.pdf && (
                        <div className="text-xs text-destructive px-2 py-1 bg-destructive/10 rounded leading-tight">
                          {exportErrors.pdf}
                          {(retryAttempts.pdf || 0) < 3 && (
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => handleExport("pdf", true)}
                              className="ml-2 h-5 px-2 text-xs"
                            >
                              <RefreshCw className="h-2 w-2 mr-1" />
                              Retry
                            </Button>
                          )}
                        </div>
                      )}
                      
                      {/* Show export progress if available */}
                      {showExportProgress.pdf && exportOperations.pdf && (
                        <div className="mt-2">
                          <ExportProgress 
                            operationId={exportOperations.pdf}
                            format="pdf"
                            onComplete={(success) => {
                              if (success) {
                                setShowExportProgress((prev) => ({ ...prev, pdf: false }));
                              }
                            }}
                            onRetry={() => handleExport("pdf", true)}
                          />
                        </div>
                      )}
                    </div>
                    
                    <div className="space-y-2">
                      <Button 
                        variant={exportErrors.docx ? "destructive" : "default"}
                        onClick={() => handleExport("docx")}
                        className="w-full justify-start text-sm h-9"
                        disabled={downloading.docx}
                      >
                        {downloading.docx ? (
                          <>
                            <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-current mr-2" />
                            Exporting...
                          </>
                        ) : exportErrors.docx ? (
                          <>
                            <AlertCircle className="h-3 w-3 mr-2" />
                            Export Failed
                          </>
                        ) : (
                          <>
                            <Download className="h-3 w-3 mr-2" />
                            Export as DOCX
                          </>
                        )}
                      </Button>
                      {exportErrors.docx && (
                        <div className="text-xs text-destructive px-2 py-1 bg-destructive/10 rounded leading-tight">
                          {exportErrors.docx}
                          {(retryAttempts.docx || 0) < 3 && (
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => handleExport("docx", true)}
                              className="ml-2 h-5 px-2 text-xs"
                            >
                              <RefreshCw className="h-2 w-2 mr-1" />
                              Retry
                            </Button>
                          )}
                        </div>
                      )}
                      
                      {/* Show export progress if available */}
                      {showExportProgress.docx && exportOperations.docx && (
                        <div className="mt-2">
                          <ExportProgress 
                            operationId={exportOperations.docx}
                            format="docx"
                            onComplete={(success) => {
                              if (success) {
                                setShowExportProgress((prev) => ({ ...prev, docx: false }));
                              }
                            }}
                            onRetry={() => handleExport("docx", true)}
                          />
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          </div>
        </div>
      </main>
      {docMeta && (docMeta.html_template || docMeta.ai_generation_metadata || docMeta.generated_sections) && (
  <div className="mt-8">
    <Accordion type="single" collapsible>
      <AccordionItem value="ai-fields">
        <AccordionTrigger>Show AI Generation Details</AccordionTrigger>
        <AccordionContent>
          {/* Original HTML Template */}
          {docMeta.html_template && (
            <div className="mb-4">
              <h4 className="font-semibold mb-1">Original HTML Template</h4>
              <pre className="bg-muted p-2 rounded text-xs overflow-x-auto max-h-48">{docMeta.html_template}</pre>
              <Button size="sm" onClick={() => navigator.clipboard.writeText(docMeta.html_template)} className="mt-1">Copy</Button>
            </div>
          )}
          {/* AI Generation Metadata */}
          {docMeta.ai_generation_metadata && (
            <div className="mb-4">
              <h4 className="font-semibold mb-1">AI Generation Metadata</h4>
              <pre className="bg-muted p-2 rounded text-xs overflow-x-auto max-h-48">{JSON.stringify(
                typeof docMeta.ai_generation_metadata === "string"
                  ? JSON.parse(docMeta.ai_generation_metadata)
                  : docMeta.ai_generation_metadata,
                null,
                2
              )}</pre>
              <Button size="sm" onClick={() => navigator.clipboard.writeText(docMeta.ai_generation_metadata)} className="mt-1">Copy</Button>
            </div>
          )}
          {/* Per-section Results */}
          {docMeta.generated_sections && (
            <div className="mb-4">
              <h4 className="font-semibold mb-1">Per-section Results</h4>
              <pre className="bg-muted p-2 rounded text-xs overflow-x-auto max-h-48">{JSON.stringify(
                typeof docMeta.generated_sections === "string"
                  ? JSON.parse(docMeta.generated_sections)
                  : docMeta.generated_sections,
                null,
                2
              )}</pre>
              <Button size="sm" onClick={() => navigator.clipboard.writeText(docMeta.generated_sections)} className="mt-1">Copy</Button>
            </div>
          )}
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  </div>
)}
    </div>
  );
};

const Label = ({ children, className }: { children: React.ReactNode; className?: string }) => (
  <div className={className}>{children}</div>
);

export default Preview;
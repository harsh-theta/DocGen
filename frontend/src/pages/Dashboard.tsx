import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useNavigate } from "react-router-dom";
import { Upload, FileText, LogOut, Sparkles } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { fetchWithAuth } from "@/lib/api";

const Dashboard = () => {
  const [file, setFile] = useState<File | null>(null);
  const [prompt, setPrompt] = useState("");
  const [documentTitle, setDocumentTitle] = useState("");
  const [documentType, setDocumentType] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [documents, setDocuments] = useState<any[]>([]);
  const [error, setError] = useState("");
  const navigate = useNavigate();
  const { toast } = useToast();

  useEffect(() => {
    // Fetch user's documents from backend
    const fetchDocs = async () => {
      try {
        const response = await fetchWithAuth("/documents");
        if (!response.ok) throw new Error("Failed to fetch documents");
        const data = await response.json();
        setDocuments(data);
      } catch (err: any) {
        setError(err.message || "Failed to fetch documents");
      }
    };
    fetchDocs();
  }, []);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
      toast({
        title: "File selected",
        description: `${selectedFile.name} is ready to upload.`,
      });
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setError("");
    try {
      const formData = new FormData();
      formData.append("file", file);
      const response = await fetchWithAuth("/upload-doc", {
        method: "POST",
        body: formData,
      });
      if (!response.ok) throw new Error("Upload failed");
      let data;
      try {
        data = await response.json();
      } catch (jsonErr) {
        throw new Error("Upload succeeded but response was not valid JSON");
      }
      toast({ title: "Upload successful", description: `${file.name} uploaded.` });
      setFile(null);
      // Navigate to preview for the new document
      if (data && typeof data.id === "string" && data.id.length > 0) {
        navigate(`/preview?id=${data.id}`);
      } else {
        setError("Upload succeeded but no document ID was returned. Please refresh and try again.");
        return;
      }
      // Optionally refresh document list
      const docsRes = await fetchWithAuth("/documents");
      setDocuments(await docsRes.json());
    } catch (err: any) {
      setError(err.message || "Upload failed");
    }
  };

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !prompt.trim() || !documentTitle.trim() || !documentType.trim()) {
      toast({
        title: "Missing information",
        description: "Please fill in all fields and upload a file.",
        variant: "destructive",
      });
      return;
    }
    
    setIsGenerating(true);
    setError("");
    
    try {
      // Upload the file first
      const formData = new FormData();
      formData.append("file", file);
      const response = await fetchWithAuth("/upload-doc", {
        method: "POST",
        body: formData,
      });
      
      if (!response.ok) throw new Error("Upload failed");
      
      const data = await response.json();
      
      if (!data || !data.id) {
        throw new Error("Upload succeeded but no document ID was returned");
      }
      
      toast({ 
        title: "Upload successful", 
        description: `${file.name} uploaded. Opening preview...` 
      });
      
      // Navigate to preview with the document ID
      navigate(`/preview?id=${data.id}`);
      
      // Reset form
      setFile(null);
      setPrompt("");
      setDocumentTitle("");
      setDocumentType("");
      
      // Refresh document list
      const docsRes = await fetchWithAuth("/documents");
      if (docsRes.ok) {
        setDocuments(await docsRes.json());
      }
      
    } catch (err: any) {
      setError(err.message || "Upload failed");
      toast({
        title: "Upload failed",
        description: err.message || "Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsGenerating(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("token");
    navigate("/");
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-background to-secondary/20">
      <header className="border-b bg-card/50 backdrop-blur-sm">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="bg-primary rounded-full p-2">
              <FileText className="h-5 w-5 text-primary-foreground" />
            </div>
            <h1 className="text-xl font-bold">DocGen</h1>
          </div>
          <Button variant="ghost" onClick={handleLogout} className="flex items-center space-x-2">
            <LogOut className="h-4 w-4" />
            <span>Logout</span>
          </Button>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        <div className="max-w-2xl mx-auto animate-slide-up">
          <div className="text-center mb-8">
            <h2 className="text-3xl font-bold mb-2">Generate Documents</h2>
            <p className="text-muted-foreground">Upload a file and describe what you want to generate</p>
          </div>

          <Card className="shadow-large border-0">
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Sparkles className="h-5 w-5 text-primary" />
                <span>Document Generator</span>
              </CardTitle>
              <CardDescription>
                Fill in the details below to generate your custom document
              </CardDescription>
            </CardHeader>
            <form onSubmit={handleGenerate}>
              <CardContent className="space-y-6">
                {/* File Upload */}
                <div className="space-y-2">
                  <Label htmlFor="file">Upload File</Label>
                  <div className="border-2 border-dashed border-muted rounded-lg p-6 text-center hover:border-primary/50 transition-colors">
                    <input
                      id="file"
                      type="file"
                      onChange={handleFileUpload}
                      className="hidden"
                      accept=".pdf,.doc,.docx"
                    />
                    <label htmlFor="file" className="cursor-pointer">
                      <Upload className="h-10 w-10 text-muted-foreground mx-auto mb-2" />
                      <p className="text-sm text-muted-foreground">
                        {file ? file.name : "Click to upload or drag and drop"}
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">
                        PDF, DOC, DOCX (Max 10MB)
                      </p>
                    </label>
                  </div>
                  {file && (
                    <Button type="button" onClick={handleUpload} className="mt-2">Upload</Button>
                  )}
                </div>

                {/* Document Title */}
                <div className="space-y-2">
                  <Label htmlFor="title">Document Title</Label>
                  <Input
                    id="title"
                    type="text"
                    placeholder="e.g., Project Proposal, Legal Contract"
                    value={documentTitle}
                    onChange={(e) => setDocumentTitle(e.target.value)}
                    className="h-11"
                  />
                </div>

                {/* Document Type */}
                <div className="space-y-2">
                  <Label htmlFor="type">Document Type</Label>
                  <Input
                    id="type"
                    type="text"
                    placeholder="e.g., Business Report, Invoice, Letter"
                    value={documentType}
                    onChange={(e) => setDocumentType(e.target.value)}
                    className="h-11"
                  />
                </div>

                {/* Prompt */}
                <div className="space-y-2">
                  <Label htmlFor="prompt">Generation Prompt</Label>
                  <Textarea
                    id="prompt"
                    placeholder="Describe what you want to generate. Be specific about format, style, and content requirements..."
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    className="min-h-[120px] resize-none"
                  />
                </div>

                <Button
                  type="submit"
                  className="w-full h-12 font-medium"
                  disabled={isGenerating}
                >
                  {isGenerating ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary-foreground mr-2"></div>
                      Generating Document...
                    </>
                  ) : (
                    <>
                      <Sparkles className="h-4 w-4 mr-2" />
                      Generate Document
                    </>
                  )}
                </Button>
                {error && <div className="text-red-500 text-sm mt-2">{error}</div>}
              </CardContent>
            </form>
          </Card>

          {/* Document List */}
          <div className="mt-10">
            <h3 className="text-xl font-bold mb-4">Your Documents</h3>
            {documents.length === 0 ? (
              <p className="text-muted-foreground">No documents uploaded yet.</p>
            ) : (
              <ul className="space-y-2">
                {documents.map((doc) => (
                  <li key={doc.id} className="border rounded p-3 flex items-center justify-between">
                    <span>{doc.name || doc.original_file_url?.split("/").pop() || "Untitled"}</span>
                    <Button size="sm" onClick={() => navigate(`/preview?id=${doc.id}`)}>Preview</Button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </main>
    </div>
  );
};

export default Dashboard;
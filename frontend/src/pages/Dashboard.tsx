import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { useNavigate } from "react-router-dom";
import { Upload, FileText, LogOut, Sparkles, AlertCircle } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { fetchWithAuth } from "@/lib/api";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

type UserInput = {
  project_name: string;
  project_description: string;
  prompt_text: string;
  json_overrides?: Record<string, any>;
  strict_vars?: Record<string, any>;
};
type GenerationRequest = {
  html_template: string;
  user_input: UserInput;
  document_id: string;
};

const Dashboard = () => {
  const [file, setFile] = useState<File | null>(null);
  const [prompt, setPrompt] = useState("");
  const [projectName, setProjectName] = useState("");
  const [projectDescription, setProjectDescription] = useState("");
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
      formData.append("title", projectName); // Send project name as title
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

  const handleAIGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !prompt.trim() || !projectName.trim() || !projectDescription.trim()) {
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
      // 1. Upload the file first
      const formData = new FormData();
      formData.append("file", file);
      formData.append("title", projectName); // Send project name as title
      const uploadRes = await fetchWithAuth("/upload-doc", {
        method: "POST",
        body: formData,
      });
      if (!uploadRes.ok) throw new Error("Upload failed");
      const uploadData = await uploadRes.json();
      if (!uploadData || !uploadData.id) {
        throw new Error("Upload succeeded but no document ID was returned");
      }
      const docId = uploadData.id;
      // 2. Fetch the parsed_structure (HTML template) for the uploaded document
      const sessionRes = await fetchWithAuth(`/session/${docId}`);
      if (!sessionRes.ok) throw new Error("Failed to fetch parsed document structure");
      const sessionData = await sessionRes.json();
      const htmlTemplate = sessionData.parsed_structure || "";
      if (!htmlTemplate) throw new Error("No parsed HTML structure found for the uploaded document");
      // 3. Build the AI generation request
      const userInput: UserInput = {
        project_name: projectName,
        project_description: projectDescription,
        prompt_text: prompt,
        json_overrides: {},
        strict_vars: {},
      };
      const genReq: GenerationRequest = {
        html_template: htmlTemplate,
        user_input: userInput,
        document_id: docId,
      };
      // 4. Call the /generate endpoint
      const genRes = await fetchWithAuth("/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(genReq),
      });
      if (!genRes.ok) {
        const errData = await genRes.json().catch(() => ({}));
        throw new Error(errData.errors?.[0] || "AI generation failed");
      }
      const genData = await genRes.json();
      if (!genData.success) {
        throw new Error(genData.errors?.[0] || "AI generation failed");
      }
      toast({
        title: "AI Generation Complete",
        description: "Your document has been generated!",
      });
      // 5. Navigate to preview for the generated document
      navigate(`/preview?id=${docId}`);
      // Reset form
      setFile(null);
      setPrompt("");
      setProjectName("");
      setProjectDescription("");
      // Refresh document list
      const docsRes = await fetchWithAuth("/documents");
      if (docsRes.ok) {
        setDocuments(await docsRes.json());
      }
    } catch (err: any) {
      setError(err.message || "AI generation failed");
      toast({
        title: "AI generation failed",
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
            <form onSubmit={handleAIGenerate}>
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
                      aria-label="Upload document file"
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
                    <Button type="button" onClick={handleUpload} className="mt-2" size="sm" variant="outline" aria-label="Upload file">Upload</Button>
                  )}
                  <p className="text-xs text-muted-foreground mt-1">Upload a sample document to use as a template for AI generation.</p>
                </div>

                {/* Project Name */}
                <div className="space-y-2">
                  <Label htmlFor="projectName">Project Name</Label>
                  <Input
                    id="projectName"
                    type="text"
                    placeholder="e.g., ZenFlow, HR Management System"
                    value={projectName}
                    onChange={(e) => setProjectName(e.target.value)}
                    className="h-11"
                    aria-label="Project name"
                  />
                  <p className="text-xs text-muted-foreground">This will be used as the project name for AI generation.</p>
                </div>

                {/* Project Description */}
                <div className="space-y-2">
                  <Label htmlFor="projectDescription">Project Description</Label>
                  <Input
                    id="projectDescription"
                    type="text"
                    placeholder="e.g., Internal HR automation tool for onboarding"
                    value={projectDescription}
                    onChange={(e) => setProjectDescription(e.target.value)}
                    className="h-11"
                    aria-label="Project description"
                  />
                  <p className="text-xs text-muted-foreground">Describe the project for which you want to generate a document.</p>
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
                    aria-label="AI generation prompt"
                  />
                  <p className="text-xs text-muted-foreground">Provide detailed instructions for the AI (e.g., style, sections, requirements).</p>
                </div>

                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        type="submit"
                        className="w-full h-12 font-medium"
                        disabled={isGenerating}
                        aria-label="Generate document with AI"
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
                            <Badge variant="secondary" className="ml-2">AI</Badge>
                          </>
                        )}
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent side="top">
                      <span>This will use AI to generate a new document based on your template and prompt.</span>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>

                {isGenerating && (
                  <CardFooter className="flex flex-col items-center">
                    <Progress value={100} className="w-full mb-2" />
                    <span className="text-xs text-muted-foreground">AI is generating your document. This may take up to a minute.</span>
                  </CardFooter>
                )}

                {error && (
                  <div className="bg-destructive/10 border border-destructive text-destructive text-sm mt-2 rounded p-2 flex items-center gap-2">
                    <AlertCircle className="h-4 w-4" />
                    {error}
                  </div>
                )}
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
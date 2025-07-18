import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useLocation, useNavigate } from "react-router-dom";
import { FileText, Download, Eye, ArrowLeft, File } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

const Preview = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { toast } = useToast();
  
  const { documentTitle, documentType, prompt, fileName } = location.state || {};

  const handleExport = (format: "pdf" | "docx") => {
    toast({
      title: "Export started",
      description: `Your document is being exported as ${format.toUpperCase()}...`,
    });
    
    // Simulate export process
    setTimeout(() => {
      toast({
        title: "Export completed",
        description: `Document exported successfully as ${format.toUpperCase()}.`,
      });
    }, 1500);
  };

  const goBack = () => {
    navigate("/dashboard");
  };

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
            <h1 className="text-xl font-bold">DocuGen</h1>
          </div>
          <div className="flex items-center space-x-2">
            <Button variant="outline" onClick={() => handleExport("pdf")} className="flex items-center space-x-2">
              <Download className="h-4 w-4" />
              <span>PDF</span>
            </Button>
            <Button onClick={() => handleExport("docx")} className="flex items-center space-x-2">
              <Download className="h-4 w-4" />
              <span>DOCX</span>
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
                    <p className="text-sm font-medium">{documentTitle || "Untitled Document"}</p>
                  </div>
                  <div>
                    <Label className="text-sm font-medium text-muted-foreground">Type</Label>
                    <p className="text-sm">{documentType || "Unknown Type"}</p>
                  </div>
                  <div>
                    <Label className="text-sm font-medium text-muted-foreground">Source File</Label>
                    <p className="text-sm flex items-center space-x-1">
                      <File className="h-3 w-3" />
                      <span>{fileName || "No file"}</span>
                    </p>
                  </div>
                  <div>
                    <Label className="text-sm font-medium text-muted-foreground">Prompt</Label>
                    <p className="text-sm text-muted-foreground">{prompt || "No prompt provided"}</p>
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
                  <Button 
                    variant="outline" 
                    onClick={() => handleExport("pdf")}
                    className="w-full justify-start"
                  >
                    <Download className="h-4 w-4 mr-2" />
                    Export as PDF
                  </Button>
                  <Button 
                    onClick={() => handleExport("docx")}
                    className="w-full justify-start"
                  >
                    <Download className="h-4 w-4 mr-2" />
                    Export as DOCX
                  </Button>
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
                        <h1 className="text-2xl font-bold">{documentTitle || "Generated Document"}</h1>
                        <p className="text-muted-foreground">{documentType || "Document Type"}</p>
                      </div>
                      
                      <div className="space-y-4">
                        <h2 className="text-xl font-semibold">Executive Summary</h2>
                        <p className="text-foreground leading-relaxed">
                          This document has been generated based on your input and specifications. The content reflects 
                          the requirements outlined in your prompt and incorporates data from the uploaded source file.
                        </p>
                        
                        <h3 className="text-lg font-semibold">Key Points</h3>
                        <ul className="list-disc list-inside space-y-2 text-foreground">
                          <li>Automated document generation based on AI analysis</li>
                          <li>Customized formatting according to document type</li>
                          <li>Integration of source file content and user specifications</li>
                          <li>Professional layout and structure</li>
                        </ul>
                        
                        <h3 className="text-lg font-semibold">Generated Content</h3>
                        <p className="text-foreground leading-relaxed">
                          Based on your prompt: "{prompt || "No specific prompt provided"}", this document has been 
                          tailored to meet your requirements. The AI has analyzed your input and created a structured 
                          document that follows best practices for {documentType || "this type of document"}.
                        </p>
                        
                        <div className="bg-muted/50 p-4 rounded-lg">
                          <p className="text-sm text-muted-foreground italic">
                            This is a preview of your generated document. The actual exported file will contain 
                            the complete content with proper formatting and styling.
                          </p>
                        </div>
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
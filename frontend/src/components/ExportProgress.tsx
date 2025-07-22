import React, { useState, useEffect } from 'react';
import { Progress } from "@/components/ui/progress";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { fetchWithAuth } from "@/lib/api";
import { AlertCircle, CheckCircle, RefreshCw, XCircle } from "lucide-react";

interface ExportProgressProps {
  operationId: string;
  format: "pdf" | "docx";
  onComplete?: (success: boolean, result?: any) => void;
  onRetry?: () => void;
  pollingInterval?: number;
}

interface OperationStatus {
  id: string;
  status: string;
  progress: number;
  message: string;
  current_step?: string;
  steps?: Array<{
    name: string;
    status: string;
    message?: string;
  }>;
  errors?: Array<{
    message: string;
    time: string;
  }>;
  result?: any;
}

const ExportProgress: React.FC<ExportProgressProps> = ({
  operationId,
  format,
  onComplete,
  onRetry,
  pollingInterval = 1000
}) => {
  const [status, setStatus] = useState<OperationStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [polling, setPolling] = useState<boolean>(true);

  useEffect(() => {
    if (!operationId || !polling) return;

    const checkStatus = async () => {
      try {
        const res = await fetchWithAuth(`/export/status/${operationId}`);
        if (!res.ok) {
          const errorData = await res.json().catch(() => ({}));
          setError(errorData.message || `Failed to check export status (${res.status})`);
          setPolling(false);
          return;
        }

        const data = await res.json();
        setStatus(data);

        // Check if operation is complete
        if (data.status === "completed") {
          setPolling(false);
          if (onComplete) onComplete(true, data.result);
        } else if (data.status === "failed") {
          setPolling(false);
          setError(data.message || "Export failed");
          if (onComplete) onComplete(false);
        }
      } catch (err: any) {
        setError(`Error checking export status: ${err.message}`);
        setPolling(false);
      }
    };

    // Initial check
    checkStatus();

    // Set up polling
    const interval = setInterval(checkStatus, pollingInterval);

    // Clean up
    return () => clearInterval(interval);
  }, [operationId, polling, pollingInterval, onComplete]);

  const handleRetry = () => {
    setError(null);
    setPolling(true);
    if (onRetry) onRetry();
  };

  // If no status yet, show initial loading
  if (!status && !error) {
    return (
      <div className="space-y-2">
        <div className="flex items-center space-x-2">
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary" />
          <span className="text-sm">Starting {format.toUpperCase()} export...</span>
        </div>
        <Progress value={5} className="h-2" />
      </div>
    );
  }

  // If error occurred
  if (error) {
    return (
      <Alert variant="destructive" className="mt-2">
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>Export Failed</AlertTitle>
        <AlertDescription className="text-xs mt-1">{error}</AlertDescription>
        <Button 
          size="sm" 
          variant="outline" 
          onClick={handleRetry} 
          className="mt-2 h-7 text-xs"
        >
          <RefreshCw className="h-3 w-3 mr-1" />
          Retry Export
        </Button>
      </Alert>
    );
  }

  // If we have status
  if (status) {
    return (
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            {status.status === "completed" ? (
              <CheckCircle className="h-4 w-4 text-green-500" />
            ) : status.status === "failed" ? (
              <XCircle className="h-4 w-4 text-red-500" />
            ) : (
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary" />
            )}
            <span className="text-sm font-medium">
              {status.message || `${format.toUpperCase()} Export: ${status.status}`}
            </span>
          </div>
          <span className="text-xs text-muted-foreground">{status.progress}%</span>
        </div>
        
        <Progress value={status.progress} className="h-2" />
        
        {/* Show current step if available */}
        {status.current_step && status.status !== "completed" && (
          <div className="text-xs text-muted-foreground mt-1">
            Current step: {status.current_step.replace(/_/g, ' ')}
          </div>
        )}
        
        {/* Show steps progress if available */}
        {status.steps && status.steps.length > 0 && (
          <div className="mt-2 space-y-1">
            {status.steps.map((step, index) => (
              <div key={index} className="flex items-center text-xs">
                {step.status === "completed" ? (
                  <CheckCircle className="h-3 w-3 text-green-500 mr-1" />
                ) : step.status === "failed" ? (
                  <XCircle className="h-3 w-3 text-red-500 mr-1" />
                ) : (
                  <div className="h-3 w-3 rounded-full border border-primary mr-1" />
                )}
                <span className={`${step.status === "completed" ? "text-muted-foreground" : ""}`}>
                  {step.name.replace(/_/g, ' ')}
                </span>
              </div>
            ))}
          </div>
        )}
        
        {/* Show errors if any */}
        {status.errors && status.errors.length > 0 && (
          <Alert variant="destructive" className="mt-2">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Export Issues</AlertTitle>
            <AlertDescription className="text-xs mt-1">
              {status.errors.map((err, index) => (
                <div key={index}>{err.message}</div>
              ))}
            </AlertDescription>
            {status.status === "failed" && (
              <Button 
                size="sm" 
                variant="outline" 
                onClick={handleRetry} 
                className="mt-2 h-7 text-xs"
              >
                <RefreshCw className="h-3 w-3 mr-1" />
                Retry Export
              </Button>
            )}
          </Alert>
        )}
      </div>
    );
  }

  return null;
};

export default ExportProgress;
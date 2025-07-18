import { useRef, useState } from "react";
import { Box, Button, FormControl, FormLabel, Input, Alert, AlertIcon, Text } from "@chakra-ui/react";

type UploadFormProps = {
  onSubmit: (file: File) => Promise<void>;
  loading?: boolean;
  error?: string;
};

const UploadForm = ({ onSubmit, loading, error }: UploadFormProps) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedFile) {
      await onSubmit(selectedFile);
    }
  };

  return (
    <Box maxW="sm" mx="auto" mt={16} p={8} borderWidth={1} borderRadius="lg" boxShadow="md" bg="white">
      <form onSubmit={handleSubmit}>
        <FormControl isRequired mb={4}>
          <FormLabel>Upload DOCX or PDF</FormLabel>
          <Input
            type="file"
            accept=".docx,application/pdf"
            onChange={handleFileChange}
            ref={inputRef}
            disabled={loading}
          />
        </FormControl>
        {selectedFile && (
          <Text fontSize="sm" mb={2}">Selected: {selectedFile.name}</Text>
        )}
        {error && (
          <Alert status="error" mb={4}>
            <AlertIcon />
            {error}
          </Alert>
        )}
        <Button type="submit" colorScheme="teal" width="full" isLoading={loading} disabled={!selectedFile}>
          Upload
        </Button>
      </form>
    </Box>
  );
};

export default UploadForm; 
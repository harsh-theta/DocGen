import { Box, Table, Thead, Tbody, Tr, Th, Td, Link, Text } from "@chakra-ui/react";

export type DocumentItem = {
  id: string;
  name: string;
  createdAt: string;
  type: "original" | "generated";
  status?: string;
  url?: string;
};

type DocumentListProps = {
  documents: DocumentItem[];
};

const DocumentList = ({ documents }: DocumentListProps) => {
  if (documents.length === 0) {
    return <Text>No documents found.</Text>;
  }
  return (
    <Box overflowX="auto">
      <Table variant="simple" mt={4}>
        <Thead>
          <Tr>
            <Th>Name</Th>
            <Th>Type</Th>
            <Th>Status</Th>
            <Th>Created</Th>
            <Th>Action</Th>
          </Tr>
        </Thead>
        <Tbody>
          {documents.map(doc => (
            <Tr key={doc.id}>
              <Td>{doc.name}</Td>
              <Td>{doc.type === "original" ? "Uploaded" : "Generated"}</Td>
              <Td>{doc.status || "-"}</Td>
              <Td>{new Date(doc.createdAt).toLocaleString()}</Td>
              <Td>
                {doc.url ? (
                  <Link href={doc.url} isExternal color="teal.500">
                    View
                  </Link>
                ) : (
                  <Text color="gray.400">N/A</Text>
                )}
              </Td>
            </Tr>
          ))}
        </Tbody>
      </Table>
    </Box>
  );
};

export default DocumentList; 
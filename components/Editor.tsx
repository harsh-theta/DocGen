import { useEditor, EditorContent, Editor as TiptapEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { Box, Spinner, ButtonGroup, IconButton, Tooltip, Divider, Button } from "@chakra-ui/react";
import { FaBold, FaItalic, FaUnderline, FaListUl, FaListOl, FaUndo, FaRedo, FaHeading } from "react-icons/fa";
import { useEffect } from "react";

interface EditorProps {
  initialContent: string;
  onChange?: (content: string) => void;
  loading?: boolean;
}

const Toolbar = ({ editor }: { editor: TiptapEditor | null }) => {
  if (!editor) return null;
  return (
    <ButtonGroup size="sm" isAttached variant="outline" mb={2}>
      <Tooltip label="Bold"><IconButton aria-label="Bold" icon={<FaBold />} onClick={() => editor.chain().focus().toggleBold().run()} isActive={editor.isActive('bold')} /></Tooltip>
      <Tooltip label="Italic"><IconButton aria-label="Italic" icon={<FaItalic />} onClick={() => editor.chain().focus().toggleItalic().run()} isActive={editor.isActive('italic')} /></Tooltip>
      <Tooltip label="Underline"><IconButton aria-label="Underline" icon={<FaUnderline />} onClick={() => editor.chain().focus().toggleUnderline?.().run()} isActive={editor.isActive('underline')} isDisabled={!editor.can().chain().focus().toggleUnderline?.().run()} /></Tooltip>
      <Divider orientation="vertical" mx={1} height="24px" />
      <Tooltip label="Heading 1"><IconButton aria-label="Heading 1" icon={<FaHeading />} onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()} isActive={editor.isActive('heading', { level: 1 })} /></Tooltip>
      <Tooltip label="Heading 2"><IconButton aria-label="Heading 2" icon={<FaHeading style={{ fontSize: 14 }} />} onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()} isActive={editor.isActive('heading', { level: 2 })} /></Tooltip>
      <Divider orientation="vertical" mx={1} height="24px" />
      <Tooltip label="Bullet List"><IconButton aria-label="Bullet List" icon={<FaListUl />} onClick={() => editor.chain().focus().toggleBulletList().run()} isActive={editor.isActive('bulletList')} /></Tooltip>
      <Tooltip label="Numbered List"><IconButton aria-label="Numbered List" icon={<FaListOl />} onClick={() => editor.chain().focus().toggleOrderedList().run()} isActive={editor.isActive('orderedList')} /></Tooltip>
      <Divider orientation="vertical" mx={1} height="24px" />
      <Tooltip label="Undo"><IconButton aria-label="Undo" icon={<FaUndo />} onClick={() => editor.chain().focus().undo().run()} /></Tooltip>
      <Tooltip label="Redo"><IconButton aria-label="Redo" icon={<FaRedo />} onClick={() => editor.chain().focus().redo().run()} /></Tooltip>
    </ButtonGroup>
  );
};

const Editor = ({ initialContent, onChange, loading }: EditorProps) => {
  const editor = useEditor({
    extensions: [StarterKit],
    content: initialContent,
    onUpdate: ({ editor }) => {
      onChange?.(editor.getHTML());
    },
  });

  useEffect(() => {
    if (editor && initialContent !== editor.getHTML()) {
      editor.commands.setContent(initialContent);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialContent]);

  if (loading) {
    return <Spinner size="lg" />;
  }

  return (
    <Box borderWidth={1} borderRadius="md" p={4} bg="white" minH="300px">
      <Toolbar editor={editor} />
      <EditorContent editor={editor} />
    </Box>
  );
};

export default Editor; 
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Keyboard } from "lucide-react";

/**
 * Component that displays keyboard shortcuts for the editor
 */
const KeyboardShortcutsHelp = () => {
  // Define keyboard shortcuts by category
  const shortcuts = {
    "Table Creation": [
      { keys: ["Cmd/Ctrl", "Alt", "T"], description: "Insert table" },
    ],
    "Table Navigation": [
      { keys: ["Tab"], description: "Move to next cell" },
      { keys: ["Shift", "Tab"], description: "Move to previous cell" },
    ],
    "Row Operations": [
      { keys: ["Cmd/Ctrl", "Alt", "↑"], description: "Add row before" },
      { keys: ["Cmd/Ctrl", "Alt", "↓"], description: "Add row after" },
      { keys: ["Cmd/Ctrl", "Alt", "Backspace"], description: "Delete row" },
    ],
    "Column Operations": [
      { keys: ["Cmd/Ctrl", "Alt", "←"], description: "Add column before" },
      { keys: ["Cmd/Ctrl", "Alt", "→"], description: "Add column after" },
      { keys: ["Cmd/Ctrl", "Alt", "Delete"], description: "Delete column" },
    ],
    "Header Operations": [
      { keys: ["Cmd/Ctrl", "Alt", "H"], description: "Toggle header row" },
    ],
    "Cell Operations": [
      { keys: ["Cmd/Ctrl", "Alt", "M"], description: "Merge cells" },
      { keys: ["Cmd/Ctrl", "Alt", "S"], description: "Split cell" },
    ],
  };

  // Helper to render a keyboard key
  const KeyCap = ({ children }: { children: React.ReactNode }) => (
    <kbd className="px-2 py-1 text-xs font-semibold text-gray-800 bg-gray-100 border border-gray-200 rounded-md dark:bg-gray-700 dark:text-gray-100 dark:border-gray-600">
      {children}
    </kbd>
  );

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="gap-1">
          <Keyboard className="h-4 w-4" />
          <span>Shortcuts</span>
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[550px] max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Keyboard Shortcuts</DialogTitle>
        </DialogHeader>
        <div className="space-y-6 py-4">
          {Object.entries(shortcuts).map(([category, shortcutList]) => (
            <div key={category} className="space-y-2">
              <h3 className="text-sm font-medium text-muted-foreground">{category}</h3>
              <div className="space-y-1">
                {shortcutList.map((shortcut, index) => (
                  <div key={index} className="flex justify-between items-center py-1 text-sm">
                    <span>{shortcut.description}</span>
                    <div className="flex gap-1">
                      {shortcut.keys.map((key, keyIndex) => (
                        <span key={keyIndex} className="flex items-center">
                          {keyIndex > 0 && <span className="mx-1">+</span>}
                          <KeyCap>{key}</KeyCap>
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default KeyboardShortcutsHelp;
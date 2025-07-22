import { Extension } from '@tiptap/core';
import Table from '@tiptap/extension-table';
import TableRow from '@tiptap/extension-table-row';
import TableHeader from '@tiptap/extension-table-header';
import TableCell from '@tiptap/extension-table-cell';
import { memo } from 'react';

// Custom table extension with enhanced styling and functionality
export const TiptapTableExtension = Extension.create({
  name: 'enhancedTable',

  addExtensions() {
    return [
      Table.configure({
        resizable: true,
        HTMLAttributes: {
          class: 'tiptap-table',
        },
        allowTableNodeSelection: true,
      }),
      TableRow.configure({
        HTMLAttributes: {
          class: 'tiptap-table-row',
        },
      }),
      TableHeader.configure({
        HTMLAttributes: {
          class: 'tiptap-table-header',
        },
      }),
      TableCell.configure({
        HTMLAttributes: {
          class: 'tiptap-table-cell',
        },
      }),
    ];
  },

  addKeyboardShortcuts() {
    return {
      // Table creation
      'Mod-Alt-t': () => this.editor.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run(),
      
      // Table navigation
      'Tab': () => {
        if (this.editor.isActive('table')) {
          return this.editor.chain().focus().goToNextCell().run();
        }
        return false;
      },
      'Shift-Tab': () => {
        if (this.editor.isActive('table')) {
          return this.editor.chain().focus().goToPreviousCell().run();
        }
        return false;
      },
      
      // Row operations
      'Mod-Alt-ArrowUp': () => {
        if (this.editor.isActive('table')) {
          return this.editor.chain().focus().addRowBefore().run();
        }
        return false;
      },
      'Mod-Alt-ArrowDown': () => {
        if (this.editor.isActive('table')) {
          return this.editor.chain().focus().addRowAfter().run();
        }
        return false;
      },
      'Mod-Alt-Backspace': () => {
        if (this.editor.isActive('table')) {
          return this.editor.chain().focus().deleteRow().run();
        }
        return false;
      },
      
      // Column operations
      'Mod-Alt-ArrowLeft': () => {
        if (this.editor.isActive('table')) {
          return this.editor.chain().focus().addColumnBefore().run();
        }
        return false;
      },
      'Mod-Alt-ArrowRight': () => {
        if (this.editor.isActive('table')) {
          return this.editor.chain().focus().addColumnAfter().run();
        }
        return false;
      },
      'Mod-Alt-Delete': () => {
        if (this.editor.isActive('table')) {
          return this.editor.chain().focus().deleteColumn().run();
        }
        return false;
      },
      
      // Header operations
      'Mod-Alt-h': () => {
        if (this.editor.isActive('table')) {
          return this.editor.chain().focus().toggleHeaderRow().run();
        }
        return false;
      },
      
      // Cell operations
      'Mod-Alt-m': () => {
        if (this.editor.isActive('table')) {
          return this.editor.chain().focus().mergeCells().run();
        }
        return false;
      },
      'Mod-Alt-s': () => {
        if (this.editor.isActive('table')) {
          return this.editor.chain().focus().splitCell().run();
        }
        return false;
      },
    };
  },
});

// Table menu component for creating and editing tables
export const TableMenu = ({ editor }: { editor: any }) => {
  if (!editor) {
    return null;
  }

  const insertTable = () => {
    editor.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run();
  };

  const deleteTable = () => {
    editor.chain().focus().deleteTable().run();
  };

  const addColumnBefore = () => {
    editor.chain().focus().addColumnBefore().run();
  };

  const addColumnAfter = () => {
    editor.chain().focus().addColumnAfter().run();
  };

  const deleteColumn = () => {
    editor.chain().focus().deleteColumn().run();
  };

  const addRowBefore = () => {
    editor.chain().focus().addRowBefore().run();
  };

  const addRowAfter = () => {
    editor.chain().focus().addRowAfter().run();
  };

  const deleteRow = () => {
    editor.chain().focus().deleteRow().run();
  };

  const toggleHeaderColumn = () => {
    editor.chain().focus().toggleHeaderColumn().run();
  };

  const toggleHeaderRow = () => {
    editor.chain().focus().toggleHeaderRow().run();
  };

  const toggleHeaderCell = () => {
    editor.chain().focus().toggleHeaderCell().run();
  };

  const mergeCells = () => {
    editor.chain().focus().mergeCells().run();
  };

  const splitCell = () => {
    editor.chain().focus().splitCell().run();
  };

  const isInTable = editor.isActive('table');

  return (
    <div className="table-menu border-b border-border bg-muted/30 p-3 flex flex-wrap gap-2 items-center">
      {!isInTable ? (
        <button
          onClick={insertTable}
          className="inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-8 px-3 py-1"
        >
          Insert Table
        </button>
      ) : (
        <>
          <button
            onClick={deleteTable}
            className="inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-destructive text-destructive-foreground hover:bg-destructive/90 h-8 px-3 py-1"
          >
            Delete Table
          </button>
          
          <div className="h-4 w-px bg-border mx-2"></div>
          
          <button
            onClick={addColumnBefore}
            className="inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-8 px-2 py-1"
          >
            + Col Before
          </button>
          <button
            onClick={addColumnAfter}
            className="inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-8 px-2 py-1"
          >
            + Col After
          </button>
          <button
            onClick={deleteColumn}
            className="inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-8 px-2 py-1"
          >
            - Col
          </button>
          
          <div className="h-4 w-px bg-border mx-2"></div>
          
          <button
            onClick={addRowBefore}
            className="inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-8 px-2 py-1"
          >
            + Row Before
          </button>
          <button
            onClick={addRowAfter}
            className="inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-8 px-2 py-1"
          >
            + Row After
          </button>
          <button
            onClick={deleteRow}
            className="inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-8 px-2 py-1"
          >
            - Row
          </button>
          
          <div className="h-4 w-px bg-border mx-2"></div>
          
          <button
            onClick={toggleHeaderRow}
            className={`inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 h-8 px-2 py-1 ${
              editor.isActive('tableHeader') 
                ? 'bg-primary text-primary-foreground hover:bg-primary/90' 
                : 'border border-input bg-background hover:bg-accent hover:text-accent-foreground'
            }`}
          >
            Header Row
          </button>
          <button
            onClick={toggleHeaderColumn}
            className="inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-8 px-2 py-1"
          >
            Header Col
          </button>
          <button
            onClick={toggleHeaderCell}
            className="inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-8 px-2 py-1"
          >
            Header Cell
          </button>
          
          <div className="h-4 w-px bg-border mx-2"></div>
          
          <button
            onClick={mergeCells}
            className="inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-8 px-2 py-1"
          >
            Merge
          </button>
          <button
            onClick={splitCell}
            className="inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-8 px-2 py-1"
          >
            Split
          </button>
        </>
      )}
    </div>
  );
};
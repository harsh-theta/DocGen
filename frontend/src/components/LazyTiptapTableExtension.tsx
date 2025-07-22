import { lazy, Suspense } from 'react';
import { Skeleton } from "@/components/ui/skeleton";

// Lazy load the TiptapTableExtension component
const TableMenuComponent = lazy(() => 
  import('./TiptapTableExtension').then(module => ({ 
    default: module.TableMenu 
  }))
);

/**
 * Lazy-loaded wrapper for the TiptapTableExtension's TableMenu component
 * This improves initial load time by only loading the table extension when needed
 */
export const LazyTableMenu = ({ editor }: { editor: any }) => {
  // If no editor is provided, return null early
  if (!editor) {
    return null;
  }

  // Check if we're in a table context
  const isInTable = editor.isActive('table');

  return (
    <Suspense fallback={
      <div className="table-menu border-b border-border bg-muted/30 p-3 flex flex-wrap gap-2 items-center">
        <Skeleton className="h-8 w-24" />
        {isInTable && (
          <>
            <div className="h-4 w-px bg-border mx-2"></div>
            <Skeleton className="h-8 w-20" />
            <Skeleton className="h-8 w-20" />
            <Skeleton className="h-8 w-16" />
          </>
        )}
      </div>
    }>
      <TableMenuComponent editor={editor} />
    </Suspense>
  );
};

// Export the TiptapTableExtension directly
// This is still needed for the editor initialization
export { TiptapTableExtension } from './TiptapTableExtension';
import { createElement, type ReactNode } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const plugins = [remarkGfm];
const components = {
  table: ({ children }: { children?: ReactNode }) => createElement(
    'div', { className: 'research-table-scroll', role: 'region', 'aria-label': 'Research comparison table', tabIndex: 0 },
    createElement('table', null, children),
  ),
};

/** Consistent prose and safe GFM tables across research, PDF and draft views. */
export default function ResearchMarkdown({ children }: { children: string }) {
  return createElement('div', { className: 'research-prose' },
    createElement(ReactMarkdown, { remarkPlugins: plugins, components, skipHtml: true }, children),
  );
}

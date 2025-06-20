import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeSanitize from 'rehype-sanitize';
import './App.css';

export default function MarkdownMessage({ content }) {
  return (
    <div className="markdown-message">
      <ReactMarkdown
        children={content}
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeSanitize]}
        components={{
          pre: ({node, ...props}) => <pre className="content" {...props} />,
          code: ({node, ...props}) => <code className="content" {...props} />,
        }}
      />
    </div>
  );
}

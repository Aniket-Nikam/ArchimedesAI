import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import ResearchMarkdown from '../src/components/ResearchMarkdown.ts';

test('research comparison syntax becomes a semantic table with readable sections', () => {
  const markup = renderToStaticMarkup(createElement(ResearchMarkdown, null,
    '## Claim comparison\n\n| Claim | Verdict | Evidence |\n| --- | --- | --- |\n| **Attention** | Partially supported | Inspect S1 |\n\n- Read the original\n- Verify scope',
  ));
  assert.match(markup, /<h2>Claim comparison<\/h2>/);
  assert.match(markup, /<table>/);
  assert.match(markup, /<th>Verdict<\/th>/);
  assert.match(markup, /<td><strong>Attention<\/strong><\/td>/);
  assert.match(markup, /<li>Read the original<\/li>/);
  assert.doesNotMatch(markup, /\| ---/);
});

test('untrusted generated HTML and executable links are not rendered', () => {
  const markup = renderToStaticMarkup(createElement(ResearchMarkdown, null,
    '<script>alert(1)</script>\n\n[unsafe](javascript:alert%281%29)\n\n[Original paper](https://arxiv.org/abs/1706.03762)',
  ));
  assert.doesNotMatch(markup, /<script|href="javascript:/);
  assert.match(markup, /href="https:\/\/arxiv.org\/abs\/1706.03762"/);
});

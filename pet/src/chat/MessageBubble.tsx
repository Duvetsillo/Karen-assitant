import { memo, useState } from 'react';
import { Check, Copy } from 'lucide-react';
import type { ChatMessage } from '../../shared/types';
import { report } from '../state/store';
import { bridge } from '../native';

/** Render model output as text; never interpret HTML or execute embedded content. */
function Content({ text }: { text: string }) {
  return text.split(/(```[\s\S]*?(?:```|$))/g).filter(Boolean).map((part, index) => {
    if (part.startsWith('```')) {
      const code = part.replace(/^```[^\n]*\n?/, '').replace(/```$/, '');
      return <pre key={index} tabIndex={0} aria-label="Código"><code>{code}</code></pre>;
    }
    return part.split(/\n\s*\n/).filter(Boolean).map((paragraph, block) => {
      const lines = paragraph.trim().split('\n');
      return lines.every(line => /^\s*[-*] /.test(line))
        ? <ul key={`${index}-${block}`}>{lines.map((line, item) => <li key={item}>{line.replace(/^\s*[-*] /, '')}</li>)}</ul>
        : <p key={`${index}-${block}`}>{paragraph}</p>;
    });
  });
}

export const MessageBubble = memo(function MessageBubble({ message }: { message: ChatMessage }) {
  const [copied, setCopied] = useState(false);
  return <article className={`message ${message.role}`} aria-busy={Boolean(message.pending)}>
    <div className="message-meta">
      <span>{message.role === 'user' ? 'Tú' : 'Karen'}</span>
      {message.pending ? <span className="message-working"><i/><i/><i/><span>Respondiendo</span></span> :
        <button className="message-copy" aria-label="Copiar mensaje" title={copied ? 'Copiado' : 'Copiar mensaje'}
          onBlur={() => setCopied(false)} onClick={() => void (bridge.copyText ? bridge.copyText(message.text) : navigator.clipboard.writeText(message.text)).then(() => setCopied(true)).catch(report)}>
          {copied ? <Check size={14}/> : <Copy size={14}/>}<span>{copied ? 'Copiado' : 'Copiar'}</span>
        </button>}
    </div>
    {message.text ? <Content text={message.text}/> : message.pending ? <p className="message-placeholder">Preparando respuesta…</p> : null}
  </article>;
});

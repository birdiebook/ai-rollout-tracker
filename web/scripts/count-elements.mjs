// R-W2 P1: elements in the prerendered HTML, for the DOM budget in budget.mjs (tested in src/lib/design/budget.test.ts).

/**
 * Elements in an HTML document: start tags outside <script>, <style> and comments.
 * @param {string} html
 * @returns {number}
 */
export function countElements(html) {
  const body = html.replace(/<!--[\s\S]*?-->/g, '').replace(/<(script|style)\b[\s\S]*?<\/\1>/gi, '<$1>');
  return (body.match(/<[a-zA-Z][\w:-]*/g) ?? []).length;
}

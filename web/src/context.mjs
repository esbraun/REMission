/** Identity is independent of cancellation: delayed responses can still settle. */
export class ContextGate {
  constructor() { this.generation = 0; this.context = ''; }
  /** @param {string} context */
  activate(context) { this.context = context; return this.capture(); }
  invalidate() { this.generation += 1; this.context = ''; }
  capture() { return { generation: this.generation, context: this.context }; }
  /** @param {{generation:number,context:string}} ticket */
  accepts(ticket) { return ticket.generation === this.generation && ticket.context === this.context; }
  /** Complete an identity notification only in the generation that started it.
   * @param {() => Promise<unknown>} operation
   * @param {() => void} success
   * @param {(error: unknown) => void} failure
   */
  async notifyAfter(operation, success, failure) {
    const ticket = this.capture();
    try { await operation(); if (this.accepts(ticket)) success(); }
    catch (error) { if (this.accepts(ticket)) failure(error); }
  }
}

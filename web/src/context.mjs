/** Identity is independent of cancellation: delayed responses can still settle. */
export class ContextGate {
  constructor() { this.generation = 0; this.context = ''; }
  /** @param {string} context */
  activate(context) { this.context = context; return this.capture(); }
  invalidate() { this.generation += 1; this.context = ''; }
  capture() { return { generation: this.generation, context: this.context }; }
  /** @param {{generation:number,context:string}} ticket */
  accepts(ticket) { return ticket.generation === this.generation && ticket.context === this.context; }
}

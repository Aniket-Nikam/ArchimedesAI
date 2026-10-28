type Node = {id:string;group:number;name?:string};
export const graphId = (value:unknown): string => typeof value==='string' ? value : String((value as {id?:string})?.id || '');

/** Deterministic, finite positions; no physics engine or canvas lifecycle dependency. */
export function graphLayout(nodes:Node[], linked:boolean) {
  const positions = new Map<string,{x:number;y:number}>();
  if (linked) {
    const groups = [1,2,3].map(group => nodes.filter(node=>node.group===group));
    groups.forEach((group,column)=>group.forEach((node,row)=>positions.set(node.id,{x:140+column*280,y:30+(row+.5)*390/Math.max(1,group.length)})));
  } else {
    const columns = Math.max(1,Math.ceil(Math.sqrt(nodes.length*1.6)));
    const rows = Math.max(1,Math.ceil(nodes.length/columns));
    nodes.forEach((node,index)=>positions.set(node.id,{x:(index%columns+.5)*840/columns,y:15+(Math.floor(index/columns)+.5)*400/rows}));
  }
  return positions;
}

import {test} from 'node:test';
import assert from 'node:assert/strict';
import {graphId,graphLayout} from '../src/graphLayout.ts';

test('unconnected results retain distinct visible finite positions',()=>{
  for(const count of [1,6,16,40]){
    const nodes=Array.from({length:count},(_,i)=>({id:String(i),group:1}));
    const positions=graphLayout(nodes,false);
    assert.equal(new Set([...positions.values()].map(p=>`${p.x},${p.y}`)).size,count);
    assert.ok([...positions.values()].every(p=>Number.isFinite(p.x)&&Number.isFinite(p.y)&&p.x>0&&p.x<840&&p.y>0&&p.y<450));
  }
});
test('citation groups occupy distinct columns with preserved paper identities',()=>{
  const positions=graphLayout([{id:'root',group:1},{id:'citing',group:2},{id:'deeper',group:3}],true);
  assert.ok(positions.get('root')!.x<positions.get('citing')!.x);
  assert.ok(positions.get('citing')!.x<positions.get('deeper')!.x);
});
test('link identity supports strings and objects without inventing IDs',()=>{
  assert.equal(graphId('paper'),'paper');
  assert.equal(graphId({id:'paper'}),'paper');
  assert.equal(graphId(null),'');
});

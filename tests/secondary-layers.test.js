const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
function fixture(){
 const nodes={},listeners={},attrs={};let observe,closed=0,focused='';
 const element=id=>nodes[id]||=( {id,open:false,classList:{contains:()=>nodes[id].open},setAttribute(k,v){attrs[id+':'+k]=v;},getClientRects:()=>[{}],focus(){focused=id;document.activeElement=this;},click(){closed++;nodes.helpModal.open=false;observe();},querySelectorAll:()=>[element('helpModalClose'),element('last')]} );
 const document={activeElement:element('toolsOpenBtn'),getElementById:element,querySelector:()=>null,addEventListener:(name,fn)=>listeners[name]=fn};
 const context={document,MutationObserver:function(fn){observe=fn;this.observe=()=>{};}};
 vm.runInNewContext(fs.readFileSync('assets/ux-fixes.js','utf8'),context);
 return {nodes,attrs,listeners,open(){nodes.helpModal.open=true;observe();},closed:()=>closed,focus:()=>focused,document};
}
test('legacy sheets acquire a dialog role and Escape closes them with focus restored',()=>{
 const f=fixture();f.open();assert.equal(f.focus(),'helpModalClose');assert.equal(f.attrs['helpModal:role'],'dialog');
 f.listeners.keydown({key:'Escape',preventDefault(){}});assert.equal(f.closed(),1);assert.equal(f.focus(),'toolsOpenBtn');
});
test('legacy sheet tab focus stays inside the sheet and composing Escape is ignored',()=>{
 const f=fixture();f.open();f.document.activeElement=f.nodes.last;
 f.listeners.keydown({key:'Tab',preventDefault(){}});assert.equal(f.focus(),'helpModalClose');
 f.listeners.keydown({key:'Escape',isComposing:true,preventDefault(){}});assert.equal(f.closed(),0);
});

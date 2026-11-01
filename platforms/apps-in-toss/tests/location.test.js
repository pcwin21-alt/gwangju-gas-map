import test from 'node:test';
import assert from 'node:assert/strict';
import {createLocationBridge} from '../src/location-bridge.js';

test('location stays dormant until requested, and concurrent actions share one SDK call', async()=>{
  let calls=0,complete;
  const api=Object.assign(()=>{calls++;return new Promise(resolve=>complete=resolve);},{getPermission:async()=> 'allowed'});
  const bridge=createLocationBridge(api,4);
  assert.equal(calls,0);
  const a=new Promise((resolve,reject)=>bridge.getCurrentPosition(resolve,reject));
  const b=new Promise((resolve,reject)=>bridge.getCurrentPosition(resolve,reject));
  await Promise.resolve();await Promise.resolve();assert.equal(calls,1);
  complete({coords:{latitude:35,longitude:126}});assert.deepEqual(await a,await b);
});

test('denied permission neither requests GPS nor reopens the consent dialog',async()=>{
  let calls=0,dialogs=0;
  const api=Object.assign(()=>{calls++;},{getPermission:async()=> 'denied',openPermissionDialog:async()=>{dialogs++;}});
  const bridge=createLocationBridge(api,4);
  await assert.rejects(new Promise((resolve,reject)=>bridge.getCurrentPosition(resolve,reject)),/지역·주소 검색/);
  assert.equal(calls,0);assert.equal(dialogs,0);
});

test('first permission request is explicit and invalid coordinates cannot update the map',async()=>{
  let dialogs=0;
  const api=Object.assign(async()=>({coords:{latitude:NaN,longitude:126}}),{getPermission:async()=> 'notDetermined',openPermissionDialog:async()=>{dialogs++;return 'allowed';}});
  const bridge=createLocationBridge(api,4);
  await assert.rejects(new Promise((resolve,reject)=>bridge.getCurrentPosition(resolve,reject)),/확인하지 못/);
  assert.equal(dialogs,1);
});

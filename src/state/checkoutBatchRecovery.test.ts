import { beforeEach, expect, it } from 'vitest';
import { loadBatch, saveBatch, forgetBatch } from './checkoutBatchRecovery';
const attempt={key:'52c07a25-e642-44b0-a89b-c049679cf920',request:{address_id:'1',sellers:[{seller_id:'2',payment_method:'COD' as const,items:[{product_id:'3',quantity:2,expected_unit_price:'1.20'}]}]}};
beforeEach(()=>sessionStorage.clear());
it('restores the complete immutable batch after reload and isolates buyers',()=>{saveBatch('4',attempt);attempt.request.sellers[0].items[0].quantity=3;expect(loadBatch('4')?.request.sellers[0].items[0].quantity).toBe(2);expect(loadBatch('5')).toBeNull();});
it('refuses to replace unresolved recovery with a changed request',()=>{saveBatch('4',attempt);expect(()=>saveBatch('4',{...attempt,key:'62c07a25-e642-44b0-a89b-c049679cf920'})).toThrow();expect(forgetBatch('4','wrong')).toBe(false);expect(loadBatch('4')).not.toBeNull();});
it('fails closed on corrupt recovery data',()=>{sessionStorage.setItem('whatnot:checkout-batch:4','{}');expect(()=>loadBatch('4')).toThrow();});
it('refuses a changed price or quantity even when the caller reuses the key',()=>{saveBatch('4',attempt);const changed=structuredClone(attempt);changed.request.sellers[0].items[0].expected_unit_price='9.99';expect(()=>saveBatch('4',changed)).toThrow();expect(loadBatch('4')?.request.sellers[0].items[0].expected_unit_price).toBe('1.20');});

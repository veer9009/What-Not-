import { afterEach,expect,it,vi } from 'vitest';
import { loadHomeListings } from './homeListings';
import { creativeApi } from './creative';
import { propertiesApi } from './properties';
import { discoveryApi } from './discovery';
vi.mock('./creative',()=>({creativeApi:{listings:vi.fn()}}));
vi.mock('./properties',()=>({propertiesApi:{list:vi.fn()}}));
vi.mock('./discovery',()=>({discoveryApi:{list:vi.fn()}}));
afterEach(()=>vi.resetAllMocks());
it('paginates and searches each source on its server with bounded page sizes',async()=>{
 vi.mocked(discoveryApi.list).mockResolvedValue([]);vi.mocked(creativeApi.listings).mockResolvedValue([]);vi.mocked(propertiesApi.list).mockResolvedValue([]);
 await loadHomeListings({query:'garden',locality:'Mumbai',remote:'true',source:{address_id:'7'},radius:2,buyer:true,page:2});
 expect(discoveryApi.list).toHaveBeenCalledWith({address_id:'7'},2,{offset:60,limit:30,q:'garden'});
 expect(creativeApi.listings).toHaveBeenCalledWith(60,'CREATIVE',{q:'garden',remote:true},30);
 expect(propertiesApi.list).toHaveBeenCalledWith(60,'Mumbai','',{q:'garden',limit:30});
});
it('reuses public source pages when only the homemade radius changes',async()=>{
 vi.mocked(discoveryApi.list).mockResolvedValue([]);vi.mocked(creativeApi.listings).mockResolvedValue([]);vi.mocked(propertiesApi.list).mockResolvedValue([]);
 const publicPages=new Map();const search={query:'',locality:'',remote:'',source:{address_id:'7'},radius:1 as const,buyer:true};
 await loadHomeListings(search,publicPages);await loadHomeListings({...search,radius:3},publicPages);
 expect(discoveryApi.list).toHaveBeenCalledTimes(2);expect(creativeApi.listings).toHaveBeenCalledTimes(2);expect(propertiesApi.list).toHaveBeenCalledTimes(1);
});
it('reuses earlier public pages after a radius reset and bounds the page cache',async()=>{
 vi.mocked(discoveryApi.list).mockResolvedValue([]);vi.mocked(creativeApi.listings).mockResolvedValue([]);vi.mocked(propertiesApi.list).mockResolvedValue([]);
 const pages=new Map();const search={query:'',locality:'',remote:'',source:{address_id:'7'},radius:3 as const,buyer:true};
 await loadHomeListings(search,pages);await loadHomeListings({...search,page:1},pages);await loadHomeListings({...search,radius:1,page:0},pages);
 expect(creativeApi.listings).toHaveBeenCalledTimes(4);expect(propertiesApi.list).toHaveBeenCalledTimes(2);
 for(let page=2;page<10;page++)await loadHomeListings({...search,page},pages);
 expect(pages.size).toBeLessThanOrEqual(12);
});
it('keeps all available listing kinds in the first six picks when one catalogue is large',async()=>{
 vi.mocked(discoveryApi.list).mockResolvedValue(Array.from({length:8},(_,i)=>({id:String(i+10),seller_id:'1',name:'Product '+i,price:'10.00'} as any)));
 vi.mocked(creativeApi.listings).mockImplementation(async(_offset,domain)=>Array.from({length:domain==='CREATIVE'?8:1},(_,i)=>({id:String(i+30),title:domain+' '+i,pricing:'QUOTATION',portfolio:[]} as any)));
 vi.mocked(propertiesApi.list).mockResolvedValue([{id:'50',title:'Property',price:'100.00'} as any]);
 const result=await loadHomeListings({query:'',locality:'',remote:'',source:{address_id:'1'},radius:3,buyer:true});
 expect(result.items.slice(0,6).map(item=>item.kind)).toEqual(['PRODUCT','CREATIVE','PROFESSIONAL','PROPERTY','PRODUCT','CREATIVE']);
 expect(result.items).toHaveLength(18);
});
it('aggregates public sources without calling buyer discovery or inventing metadata',async()=>{
 vi.mocked(creativeApi.listings).mockImplementation(async(_offset,domain)=>[{id:domain==='CREATIVE'?'1':'2',provider_id:'4',title:domain+' service',description:'Real listing',category:'Service',pricing:'QUOTATION',amount:null,currency:'INR',remote:true,locality:null,portfolio:[],is_active:true,status:'APPROVED',rejection_reason:null}]);
 vi.mocked(propertiesApi.list).mockResolvedValue([{id:'3',creator_id:'4',title:'Real apartment',description:'Public listing',category:'Residential',price:'7800000.00',locality:'Mumbai',status:'APPROVED',expires_at:'2027-01-01',updated_at:'2026-11-26',rejection_reason:null,capacity:'OWNER',display_name:'Owner'}]);
 const result=await loadHomeListings({query:'',locality:'',remote:'',source:null,radius:3,buyer:false});
 expect(discoveryApi.list).not.toHaveBeenCalled();expect(result.items.map(item=>item.kind)).toEqual(['CREATIVE','PROFESSIONAL','PROPERTY']);
 expect(result.items[0]).toMatchObject({price:null,image:null,rating:null,distance:null});
 expect(result.items[2].price).toBe('7800000.00');expect(result.items[2].image).toBeNull();
});
it('keeps successful sources when one fails and searches only the loaded property records',async()=>{
 vi.mocked(creativeApi.listings).mockRejectedValueOnce(Error('private SQL')).mockResolvedValueOnce([]);
 vi.mocked(propertiesApi.list).mockResolvedValue([{id:'3',title:'Garden apartment',locality:'Mumbai',price:'100.00'} as any,{id:'4',title:'Studio',locality:'Pune',price:'200.00'} as any]);
 vi.mocked(discoveryApi.list).mockResolvedValue([{id:'5',seller_id:'6',name:'Garden basket',description:'Craft',category:'Crafts',shop_name:'Maker',price:'250.00',stock_quantity:2,image_url:'/api/v1/product-images/1',delivery_radius_km:2,is_verified:false}]);
 const result=await loadHomeListings({query:'garden',locality:'Mumbai',remote:'true',source:{address_id:'7'},radius:2,buyer:true});
 expect(result.items.map(item=>item.id)).toEqual(['5','3']);expect(result.errors).toEqual(['Creative Services could not be loaded.']);
 expect(discoveryApi.list).toHaveBeenCalledWith({address_id:'7'},2,{offset:0,limit:30,q:'garden'});expect(creativeApi.listings).toHaveBeenCalledWith(0,'PROFESSIONAL',{q:'garden',remote:true},30);
 expect(result.items[0].distance).toBeNull();expect(JSON.stringify(result)).not.toContain('private SQL');
});
it('uses only actual service portfolio images and aggregate reviews',async()=>{
 vi.mocked(creativeApi.listings).mockResolvedValueOnce([{id:'2',title:'Editing',pricing:'FIXED',amount:'1499.00',portfolio:['javascript:alert(1)','https://images.example.test/work.webp'],rating_average:'4.8',review_count:3} as any]).mockResolvedValueOnce([]);
 vi.mocked(propertiesApi.list).mockResolvedValue([]);
 const result=await loadHomeListings({query:'',locality:'',remote:'',source:null,radius:3,buyer:false});
 expect(result.items[0]).toMatchObject({image:'https://images.example.test/work.webp',rating:'4.8',reviews:3,price:'1499.00',distance:null});
});

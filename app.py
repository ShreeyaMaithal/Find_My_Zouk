"""Find My Zouk v0.2 — a visual, step-by-step shopping quiz.
Product photographs and links are fetched directly from Zouk's public Shopify storefront.
This is an independent demonstration prototype, not affiliated with Zouk.
"""
import html
import re
from pathlib import Path
from urllib.parse import urljoin
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Find My Zouk | Your bag, your vibe", page_icon="👜", layout="wide", initial_sidebar_state="collapsed")
BASE = "https://zouk.co.in"
COLLECTIONS = ["office-bag", "new-collection", "pro-laptop-bags", "office-collection", "newly-launched"]
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; FindMyZoukDemo/0.2)", "Accept": "application/json,text/html"}

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Playfair+Display:wght@600;700&display=swap');
.stApp {background:#FFF9F2;color:#33292B;font-family:'DM Sans',sans-serif}
.block-container {max-width:1060px;padding-top:1.6rem;padding-bottom:3rem}
h1,h2,h3 {font-family:'Playfair Display',Georgia,serif!important;color:#652832!important}
.hero {border-radius:25px;padding:34px 38px;background:linear-gradient(115deg,#F5D8CC,#FFF5E9);border:1px solid #EED4C8}
.eyebrow {color:#9A4B4E;letter-spacing:2px;font-size:12px;font-weight:800;text-transform:uppercase}
.hero h1 {font-size:3.2rem;margin:8px 0!important}
.hero p {font-size:1.13rem;color:#634D4B}
.step {color:#A65C5C;font-size:13px;font-weight:700;letter-spacing:1px}
div.stButton>button {border:1px solid #E8CEC5;border-radius:16px;background:#FFFCF8;color:#51373B;min-height:66px;font-weight:700;white-space:normal;transition:all .15s ease}
div.stButton>button:hover {border-color:#963D4B;color:#963D4B;background:#FBE9E1;transform:translateY(-2px)}
div.stButton>button[kind='primary'] {background:#843645;color:#fff;border-color:#843645}
div.stButton>button[kind='primary']:hover {background:#682636;color:#fff}
[data-testid='stImage'] img {border-radius:16px;object-fit:cover}
[data-testid='stProgress']>div>div {background:#A34953}
.result {padding:12px 0}
.note {background:#F9EDE5;border:1px solid #EED8CD;border-radius:14px;padding:14px 18px;color:#64474B}
#MainMenu,footer {visibility:hidden}
</style>""",unsafe_allow_html=True)

@st.cache_data(ttl=21600,show_spinner=False)
def fetch_storefront():
    """Use Shopify's publicly exposed collection JSON; never fabricate photo URLs."""
    session = requests.Session()
    records, seen, errors = [], set(), []
    for collection in COLLECTIONS:
        url=f"{BASE}/collections/{collection}/products.json?limit=250"
        try:
            response=session.get(url,headers=HEADERS,timeout=12)
            response.raise_for_status()
            products=response.json().get('products',[])
            for p in products:
                handle=p.get('handle','')
                if not handle or handle in seen: continue
                title=html.unescape(p.get('title','')).strip()
                if not any(t in title.lower() for t in ['bag','tote','backpack','sling','satchel','handbag']):continue
                imgs=p.get('images') or []
                image=(p.get('image') or {}).get('src') or (imgs[0].get('src') if imgs else '')
                if image.startswith('//'):image='https:'+image
                if image.startswith('/'):image=urljoin(BASE,image)
                variants=p.get('variants') or []
                variant=next((v for v in variants if v.get('available')),variants[0] if variants else {})
                try:price=float(variant.get('price') or 0)
                except (ValueError,TypeError):price=0
                if not image or not price:continue
                text=(title+' '+str(p.get('product_type',''))).lower()
                if 'laptop' in text or 'backpack' in text:purpose='Work & college'
                elif 'office' in text or 'business' in text:purpose='Work & college'
                elif 'duffel' in text or 'travel' in text:purpose='Travel'
                else:purpose='Everyday'
                colours=['black','brown','blue','green','pink','beige','red','yellow','orange','white']
                colour=next((c.title() for c in colours if c in text),'Multicolour')
                style='Minimal' if any(w in text for w in ['jet black','solid','noir']) else 'Statement prints'
                records.append({'name':title,'price':price,'image':image,'url':f'{BASE}/products/{handle}',
                                'purpose':purpose,'colour':colour,'style':style,
                                'available':bool(variant.get('available',True)),
                                'product_type':p.get('product_type','Bag'),'handle':handle})
                seen.add(handle)
        except (requests.RequestException,ValueError,KeyError) as exc:
            errors.append(f'{collection}: {str(exc)[:110]}')
    return records,errors

@st.cache_data(show_spinner=False)
def fallback_catalogue():
    path=Path(__file__).with_name('zouk_catalogue_snapshot.csv')
    return pd.read_csv(path) if path.exists() else pd.DataFrame()

QUESTIONS=[
 {'title':'Where will your Zouk go with you?','subtitle':'Picture your everyday adventure.','options':[('💼','Office days','Office'),('🎓','Campus life','College'),('✈️','Weekend escapes','Travel'),('☕','Everyday outings','Everyday')]},
 {'title':'What is your bag personality?','subtitle':'Pick the aesthetic that feels most you.','options':[('🎨','Bold & printed','Statement prints'),('🤎','Classic & understated','Minimal'),('🌺','A little bit of both','Versatile')]},
 {'title':'What are you carrying?','subtitle':'Your essentials help us find the right silhouette.','options':[('💻','Laptop & work gear','Laptop'),('📚','Books & notebooks','Books'),('📱','Phone, wallet & little things','Essentials'),('🧳','Everything but the kitchen sink','Everything')]},
 {'title':'What feels like your colour story?','subtitle':'No wrong answers — go with your gut.','options':[('🖤','Black & neutrals','Black'),('💙','Cool blues','Blue'),('🍫','Warm earthy tones','Brown'),('🌈','Surprise me with colour','Any')]},
 {'title':'What is your happy price?','subtitle':'We’ll try to stay within your comfort zone.','options':[('✨','Under ₹1,500',1500),('👜','₹1,500–₹2,000',2000),('💫','₹2,000–₹3,000',3000),('👑','₹3,000+',999999)]},
]

if 'step' not in st.session_state:st.session_state.step=0
if 'answers' not in st.session_state:st.session_state.answers={}

def select_answer(value):
    st.session_state.answers[st.session_state.step]=value
    st.session_state.step+=1
    st.rerun()

def reset():
    st.session_state.step=0
    st.session_state.answers={}
    st.rerun()

st.markdown('<div class="hero"><div class="eyebrow">✦ YOUR STYLE. YOUR STORY. YOUR ZOUK.</div><h1>Find My Zouk 👜</h1><p>Five little questions. One bag that feels like <em>you</em>.</p></div>',unsafe_allow_html=True)
st.write('')

step=st.session_state.step
if step<len(QUESTIONS):
    q=QUESTIONS[step]
    st.markdown(f'<div class="step">THE STYLE QUIZ · QUESTION {step+1} OF {len(QUESTIONS)}</div>',unsafe_allow_html=True)
    st.progress((step+1)/len(QUESTIONS))
    st.header(q['title'])
    st.write(q['subtitle'])
    st.write('')
    opts=q['options']
    columns=st.columns(2)
    for i,(emoji,label,value) in enumerate(opts):
        with columns[i%2]:
            if st.button(f'{emoji}   {label}',key=f'option_{step}_{i}',use_container_width=True):select_answer(value)
    st.write('')
    left,right=st.columns([1,4])
    with left:
        if step>0 and st.button('← Back',use_container_width=True):
            st.session_state.step-=1;st.rerun()
    with right:
        if st.button('Start over ↺',use_container_width=False):reset()
else:
    st.markdown('<div class="step">THE REVEAL · MADE FOR YOUR KIND OF DAY</div>',unsafe_allow_html=True)
    st.progress(1.0)
    st.header('Your Zouk matches are in! ✨')
    answers=st.session_state.answers
    with st.spinner('Finding your matches in Zouk’s real catalogue…'):
        products,errors=fetch_storefront()
    if not products:
        st.error('We could not retrieve Zouk’s live product images right now. The quiz is working, but we won’t substitute unrelated or fabricated product photos.')
        st.info('Check your internet connection and try again. You can also browse the official collection below.')
        st.link_button('Browse Zouk office bags',f'{BASE}/collections/office-bag')
        if st.button('↺ Try again'):fetch_storefront.clear();st.rerun()
    else:
        def match(p):
            score=0;reasons=[]
            purpose,style,carry,colour,budget=[answers[i] for i in range(5)]
            title=p['name'].lower()
            if purpose in ('Office','College') and p['purpose']=='Work & college':score+=30;reasons.append('Designed for a work or campus routine')
            elif purpose=='Travel' and ('travel' in title or 'duffel' in title or 'backpack' in title):score+=30;reasons.append('A practical travel-friendly category')
            elif purpose=='Everyday' and p['purpose']=='Everyday':score+=30;reasons.append('Great everyday-bag category')
            if style=='Versatile':score+=10
            elif style==p['style']:score+=18;reasons.append('Matches your preferred aesthetic')
            if carry=='Laptop' and ('laptop' in title or 'office' in title or 'backpack' in title):score+=22;reasons.append('A work-focused silhouette (verify laptop dimensions)')
            elif carry=='Books' and any(t in title for t in ['tote','office','backpack']):score+=16;reasons.append('Roomier bag style for books')
            elif carry=='Essentials' and any(t in title for t in ['sling','handbag','satchel']):score+=16;reasons.append('A lighter everyday silhouette')
            elif carry=='Everything' and any(t in title for t in ['tote','backpack','duffel','office']):score+=16;reasons.append('A carry-more bag category')
            if colour=='Any':score+=6
            elif p['colour']==colour:score+=12;reasons.append('Your chosen colour family')
            if p['price']<=budget:score+=20;reasons.append('Within your chosen budget')
            else:score-=min(30,(p['price']-budget)/120)
            if p['available']:score+=8
            else:score-=25
            return round(score),reasons
        ranked=sorted(products,key=lambda p:match(p)[0],reverse=True)
        # Prefer in-stock options; results remain heuristic, not measured probabilities.
        ranked=[p for p in ranked if p['available']][:4] or ranked[:4]
        st.caption(f"Based on your vibe: {answers[0]} · {answers[1]} · {answers[2]} · {answers[3]}")
        st.markdown(f'<div class="note">✨ Exploring <b>{len(products)} real Zouk products</b> from the official storefront. Prices and stock reflect the latest successful fetch, not a guaranteed checkout price.</div>',unsafe_allow_html=True)
        st.write('')
        cols=st.columns(2)
        for i,p in enumerate(ranked):
            _,reasons=match(p)
            with cols[i%2]:
                with st.container(border=True):
                    st.image(p['image'],use_container_width=True)
                    st.caption('🌟 YOUR TOP MATCH' if i==0 else f'ALSO YOUR VIBE · PICK {i+1}')
                    st.subheader(p['name'])
                    st.markdown(f"**₹{p['price']:,.0f}**  ·  {p['product_type'] or 'Bag'}")
                    st.write(' · '.join(reasons[:3]) if reasons else 'A fun alternative to explore.')
                    st.link_button('See this bag on Zouk ↗',p['url'],use_container_width=True)
        st.caption('Matching is an explainable prototype heuristic. Bag capacity, laptop compatibility, product availability and final price must be verified on the official product page.')
        if errors:
            with st.expander('Catalogue sync details'):
                st.write('Some collections were unavailable, but the products above came from successful official-storefront responses.')
                st.code('\n'.join(errors))
    st.write('')
    if st.button('💗 Take the quiz again',type='primary',use_container_width=True):reset()

with st.expander('About this prototype & photo sourcing'):
    st.write('Product photographs, product titles, current listed prices and product links are requested at runtime from publicly exposed JSON on zouk.co.in. The app does not bundle or invent Zouk photographs. If the storefront blocks requests or changes its API, photos may be unavailable until an authorised feed or manual catalogue is supplied.')
    st.write('This independent proof of concept is not endorsed by Zouk. Recommendations use rule-based matching, not a trained AI model. Colour and use-case labels are inferred from titles/categories and may be imperfect.')
    st.write('For a production launch, use a brand-authorised catalogue/feed, verified product attributes and approved image usage.')

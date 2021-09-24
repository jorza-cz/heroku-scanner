import json
import requests
from datetime import datetime, timedelta
import time
import re
import numpy as np
import nltk
nltk.download('stopwords')
from nltk.corpus import stopwords
import pandas as pd
import os
import streamlit as st

DENYLIST = [r'\d+\%', r'\d+\s\%', 'nuevo', 'descuento', 'usado', 'oferta', 'liquidaci', '%off', 'off!', 'envio', 'envío', 'gratis', 'llega', 'hoy', 'cuotas', 'sin interes', 'talle']
DENYLIST_POR = [r'\d+\%', r'\d+\s\%', 'nuevo', 'descuento', 'usado', 'oferta', 'liquidaci', '%off', 'off!', 'envio', 'envío', 'gratis', 'llega', 'hoy', 'cuotas', 'sin interes', 'talle']

HEADERS = {
  'x-caller-id': '593253618',
  'Content-Type': 'application/json'
}

url = st.text_input("Ingrese la URL", 'https://www.mercadolibre.com.ar/MLA871163849')
m = re.search('(M..-\d{7,10})|(M..\d{7,10})', url)
it_cat = m.group(0)
it_cat = it_cat.split('-')
it_cat = "".join(it_cat)





def check_bad_words(denylist, title):
    title = title.lower()
    for pattern in denylist:
        if re.search(pattern, title):
            return 0
    return 2

def listing_by_site(site_id, type):
    if site_id in ['MPE', 'MLV', 'MLU']:
        listings = {"free":'Gratuita', "bronze":'Clásica', "gold_special" : 'Premium'}
    else:
        listings = {"free":'Gratuita', "gold_special":'Clásica', "gold_pro" : 'Premium', "gold_premium" : 'Premium'}
    return listings[type]
    
    
def datetime_difference(string1, string2):
    return (datetime.strptime(string2[:19], '%Y-%m-%dT%H:%M:%S') - datetime.strptime(string1[:19], '%Y-%m-%dT%H:%M:%S')).seconds

def answer_score(minutes):
    if minutes <= 2:
        return 10
    elif minutes <= 5:
        return 5
    elif minutes <= 10:
        return 3
    elif minutes <= 60:
        return 1    
    else:
        return 0

def run_scanner(item_id):
    output = dict()
    scanner = dict()

    item_response = requests.get(f"https://api.mercadolibre.com/items/{it_cat}")
    #catalog_response = requests.get(f"https://api.mercadolibre.com/products/{it_cat}")
    
    if item_response.status_code == 200:
           item_info = item_response.json()
           st.write(it_cat)
    else:
        catalog_response = requests.get(f"https://api.mercadolibre.com/products/{it_cat}")
        catalog_info = catalog_response.json()
        cat_winner_id = catalog_info['buy_box_winner']['item_id']
        item_response = requests.get(f"https://api.mercadolibre.com/items/{cat_winner_id}")
        item_info = item_response.json()
        st.write(cat_winner_id)

    for name in ['title', 'price', 'image', 'specs','category', 'shipping', 'listing_type', 'answers', 'seller_level', 'catalog', 'ranking']:
        scanner[name] = {'score': 5}

    # Check title
    item_title = item_info['title'].lower()
    item_site = item_info['site_id']
    item_category = item_info['category_id']

    # # Check brand and model
    # brand = next((attr for attr in item_info['attributes'] if attr['id'] == 'BRAND'), None)
    # if brand:
    #     brand_name = brand['value_name'].lower()
    #     brand_score = 2
    #     for word in brand_name.split(' '):
    #         if not re.search(word, item_title):
    #             brand_score = 0
    #             break
    #     brand_message = f'El título de la publicación no contiene el nombre de la marca "{brand_name}".' if (brand_score == 0) else 'Ok marca.'
    # else:
    #     brand_score = 1
    #     brand_message = 'El título de la publicación no contiene el nombre de la marca...'

    # model = next((attr for attr in item_info['attributes'] if attr['id'] == 'MODEL'), None)
    # if model:
    #     model_name = model['value_name'].lower()
    #     model_score = 2
    #     for word in model_name.split(' '):
    #         if not re.search(word, item_title):
    #             model_score = 0
    #             break
    #     model_message = f'El título de la publicación no contiene el nombre del modelo "{model_name}".' if (brand_score == 0) else 'Ok modelo.'
    # else:
    #     model_score = 1
    #     model_message = 'El título de la publicación no contiene el nombre del modelo...'

    #Check trends
    tendences = requests.get(f"https://api.mercadolibre.com/trends/{item_site}/{item_category}")
    tend_json = tendences.json()
    kws = []
    for d in tend_json:
        kws.append(d['keyword'])
    words = " ".join(kws).split()  
    unique = []
    for word in words:
        if word not in unique:
            unique.append(word)
    if item_site == "MLB":
      filtered_words = [word for word in unique if word not in stopwords.words('portuguese')]
    else:
      filtered_words = [word for word in unique if word not in stopwords.words('spanish')]    
    matches_count = 0
    matches = []
    for i in filtered_words:
        if i in item_title:
           matches_count +=1   
           matches.append(i) 

    #Generate URL for trends
    cat_nr = item_category[3:]
    if item_site == 'MLA':
      trend_url = f'https://tendencias.mercadolibre.com.ar/{cat_nr}'
    elif item_site == 'MLM':
      trend_url = f'https://tendencias.mercadolibre.com.mx/{cat_nr}'
    elif item_site == 'MLB':
      trend_url = f'https://tendencias.mercadolivre.com.br/{cat_nr}'
    elif item_site == 'MLC':
      trend_url = f'https://tendencias.mercadolibre.cl/{cat_nr}'
    elif item_site == 'MLU':
      trend_url = f'https://tendencias.mercadolibre.com.uy/{cat_nr}'  
    elif item_site == 'MCO':
      trend_url = f'https://tendencias.mercadolibre.com.co/{cat_nr}' 


    #Check lenght of title
    if len(item_title) < 20:
        len_title_score = 0
        len_message = f'MUY MAL. El título de tu publicación contiene {len(item_title)} caracteres, recuerda que puedes usar hasta 60!'
    elif len(item_title) < 30:
        len_title_score = 1
        len_message = f'MAL. El título de tu publicación contiene {len(item_title)} caracteres, recuerda que puedes usar hasta 60!'
    elif len(item_title) < 40:
        len_title_score = 2
        len_message = f'REGULAR. El título de tu publicación contiene {len(item_title)} caracteres, recuerda que puedes usar hasta 60!'    
    elif len(item_title) < 50:
        len_title_score = 3
        len_message = f'BIEN. El título de tu publicación contiene {len(item_title)} caracteres, recuerda que puedes usar hasta 60!'    
    else: 
        len_title_score = 4
        len_message = f'MUY BIEN. El título de tu publicación contiene {len(item_title)} caracteres, recuerda que puedes usar hasta 60!'

    # Check denylist words in title
    bad_words_score = check_bad_words(DENYLIST, item_title)
    bad_words_title_message = 'MAL. El título contiene palabras o términos irrelevantes.' if (bad_words_score == 0) else 'BIEN. El título no contiene palabras o términos irrelevantes.'
    

    #Check trends kw in title
    if matches_count == 0:
        trend_score = 0
        trend_message = 'MAL. El título no contiene palabras en las tendencias actuales de la categoría'
    if matches_count < 4:
        trend_score = 1
        trend_message = f'REGULAR. El título contiene {matches_count} palabra/s en las tendencias actuales de la categoría'  
    if matches_count >= 4:
        trend_score = 2
        trend_message = f'BIEN. El título contiene {matches_count} palabras en las tendencias actuales de la categoría'
    
    
    
    scanner['title']['score'] = 2 + len_title_score + bad_words_score + trend_score
    scanner['title']['len_message'] = len_message
    scanner['title']['bad_words_title_message'] = bad_words_title_message
    scanner['title']['trend_message'] = trend_message
    scanner['title']['matches'] = matches
    scanner['title']['matches_count'] = matches_count
    scanner['title']['trends_url'] = trend_url

    #Check Price Discount
    if item_info['original_price'] and item_info['original_price'] > item_info['price']:
        price_score = 5
        price_message = f'BIEN. El precio tiene descuento!'
    else:
        if "loyalty_discount_eligible" in item_info['tags']:
            price_score = 0
            price_message = f'MAL. No tienes desuento y tu publicación es elegible! Aprovechalo!'
        else:
            price_score = 0
            price_message = f'MAL. No tienes descuento y tu publicación no es elegible para descuento!'  
    
    scanner['price']['score'] = price_score
    scanner['price']['price_message'] = price_message


     # Check image quality
    if 'good_quality_picture' in item_info['tags']:
        picture_score = 2
        picture_message = "BIEN. Tu imagen de portada es buena"
    else:
        picture_score = 0
        picture_message = "MAL. Tu imagen de portada es mala...."
        
    if 'good_quality_thumbnail' in item_info['tags']:
        thumbnail_score = 3
        thumbnail_message = "BIEN. Tus imágenes de la publicación estan muy bien"
    else:
        thumbnail_score = 0
        thumbnail_message = "MAL. Debes mejorar las imágenes dentro de tu publicación...."    

    #Check Len Pictures
    len_pictures = len(item_info['pictures'])
    
    if len_pictures <= 1:
        len_picture_score = 0
        len_picture_message = f'MAL. LA publicación contiene {len_pictures} imágenes. Deberías incorporar 10!'
    elif len_pictures > 1 and len_pictures < 4:
        len_picture_score = 1
        len_picture_message = f'REGULAR. La publicación contiene {len_pictures} imágenes. Deberías incorporar 10!'
    elif len_pictures >= 4 and len_pictures < 7:
        len_picture_score = 3
        len_picture_message = f'BIEN. La publicación contiene {len_pictures} imágenes. Podrías incorporar hasta 10!' 
    elif len_pictures >= 7 and len_pictures < 10:
        len_picture_score = 4
        len_picture_message = f'MUY BIEN. La publicación contiene {len_pictures} imágenes. Podrías incorporar hasta 10!'    
    else:
        len_picture_score = 5
        len_picture_message = f'EXCELENTE. La publicación contiene {len_pictures} imágenes!'    

    scanner['image']['score'] = picture_score + thumbnail_score + len_picture_score
    scanner['image']['picture_message'] = picture_message
    scanner['image']['thumbnail_message'] = thumbnail_message
    scanner['image']['len_picture_message'] = len_picture_message 

    # Technical Specs
    if 'incomplete_technical_specs' in item_info['tags']:
        scanner['specs']['score'] = 0
        scanner['specs']['message'] = "Mejora tu publicación completando su ficha técnica." 
    else:
        scanner['specs']['score'] = 5
        scanner['specs']['message'] = "Tu publicación posee una ficha técnica completa." 

   

# Category
    pred_category_response = requests.get(f"https://api.mercadolibre.com/sites/{item_site}/domain_discovery/search?q={item_title}")
    if pred_category_response.status_code == 200:
        pred_category = pred_category_response.json()
        if pred_category and 'category_id' in pred_category[0]:
            if (pred_category[0]['category_id'] == item_info['category_id']):
                scanner['category']['score'] = 5
                scanner['category']['category_message'] = "BIEN. Tu producto está publicado en la categoría correcta."
            elif 'category_name' in pred_category[0]:
                new_category = pred_category[0]['category_name']
                scanner['category']['score'] = 0
                scanner['category']['category_message'] = f'MAL. Tal vez debas publicar tu producto en la categoría "{new_category}".'
        else:
            scanner['category']['score'] = 2
            scanner['category']['category_message'] = f'No pudimos determinar la categoría adecuada para tu producto.'

   # Shipping
    
    shipping_opt = ['fulfillment', 'self_service', 'cross_docking']
    logistic_type = item_info['shipping']['logistic_type']
    category_response = requests.get(f"https://api.mercadolibre.com/categories/{item_info['category_id']}")
    
    
    if category_response.status_code == 200:
        category_details = category_response.json()
        
    if 'me2' in category_details['settings']['shipping_modes']:    
    
        if 'shipping' in item_info:
            if 'me2' in item_info['shipping']['mode']:
    
    
                if any(x in logistic_type for x in shipping_opt):
    
                
                    if 'free_shipping' in item_info['shipping'] and item_info['shipping']['free_shipping']:
                        scanner['shipping']['score'] = 10 
                        scanner['shipping']['shipping_message'] = "EXCELENTE. Ofreces el mejor servicio de envío gratis!"
                    else:
                        scanner['shipping']['score'] = 5 
                        scanner['shipping']['shipping_message'] = "MUY BIEN. Podrías ofrecer envíos gratis para mejorar tu publicación."
                else: 
                    if 'free_shipping' in item_info['shipping'] and item_info['shipping']['free_shipping']:
                        scanner['shipping']['score'] = 5 
                        scanner['shipping']['shipping_message'] = "REGULAR. Ofreces ME2 gratis pero podrías mejorar con Full, Flex o Colecta!"
                    else:
                        scanner['shipping']['score'] = 0 
                        scanner['shipping']['shipping_message'] = "MAL. Podrías ofrecer envíos dentro de Full, Flex o Colecta para mejorar tu publicación."    
            else:
                scanner['shipping']['score'] = 0
                scanner['shipping']['shipping_message'] = "MAL. No ofrecer Mercado Envíos le quita relevancia a tu publicación."
    else:
        scanner['shipping']['score'] = 5 
        scanner['shipping']['shipping_message'] = "NO APLICA. Tu publicación no aplica a ME2"

# Listing type
    listing_type = listing_by_site(item_site, item_info['listing_type_id'])
    if listing_type == 'Premium':
        scanner['listing_type']['score'] = 5
        scanner['listing_type']['listing_message'] = "Tu publicación es de tipo Premium."
    elif listing_type == 'Clásica':
        scanner['listing_type']['score'] = 3
        scanner['listing_type']['listing_message'] = "Tu publicación es de tipo Clásica. Intenta mejorarla a Premium."
    else:
        scanner['listing_type']['score'] = 0
        scanner['listing_type']['listing_message'] = "Tu publicación es de tipo Gratuita. Intenta mejorarla a Clásica o Premium."


  
     #Answer time
    answers_response = requests.get(f"https://api.mercadolibre.com/questions/search?item={item_id}")
    if answers_response.status_code == 200:
        questions = answers_response.json()['questions']
        if questions:
            answer_times = []
            for q in questions:
                if q['status'] == 'ANSWERED' and 'answer' in q and 'date_created' in q['answer']:
                    answer_times.append(datetime_difference(q['date_created'], q['answer']['date_created']))
            median_response_time = np.median(answer_times)
            scanner['answers']['time'] = int(median_response_time // 60)
        else:
             scanner['answers']['time'] = 0 #TODO ver mensaje si no tiene preguntas
            
    else:
        scanner['answers']['time'] = 0

    if scanner['answers']['time']:
        scanner['answers']['score'] = answer_score(scanner['answers']['time'])
        if scanner['answers']['score'] == 0:
            scanner['answers']['message'] = f"Tu tiempo de respuesta promedio es de {scanner['answers']['time']} minutos. Podrías estar perdiendo ventas!"
        elif scanner['answers']['score'] < 10:
            scanner['answers']['message'] = "Intenta mejorar los tiempos de respuesta para conseguir mas ventas!"
        else:
            scanner['answers']['message'] = "Tu tiempo promedio de respuesta es excelente. Sigue así!"
    else:
        scanner['answers']['score'] = 5
        scanner['answers']['message'] = "No pudimos medir tus tiempos de respuesta."

    # Reputation
    seller_id = item_info['seller_id']
    seller_response = requests.get(f"https://api.mercadolibre.com/users/{seller_id}")
    seller_reputation = seller_response.json()['seller_reputation']
    if 'level_id' in seller_reputation and seller_reputation['level_id']:
        scanner['seller_level']['level'] = int(seller_reputation['level_id'][0])
    else:
        scanner['seller_level']['level'][0] = 0

    if int(seller_reputation['level_id'][0]) == 1:
        scanner['seller_level']['score'] = 0
        scanner['seller_level']['reputation_message'] = "Tu reputación esta en rojo! Estás perdiendo el 70% de tu facturación"
    elif int(seller_reputation['level_id'][0]) == 2:
        scanner['seller_level']['score'] = 2
        scanner['seller_level']['reputation_message'] = "Tu reputación esta en naranja! Estás perdiendo casi el 70% de tu facturación"
    elif int(seller_reputation['level_id'][0]) == 3:
        scanner['seller_level']['score'] = 3
        scanner['seller_level']['reputation_message'] = "Tu reputación esta en amarillo! Podrías perder el 70% de tu facturación si no la mejoras pronto!"    
    elif int(seller_reputation['level_id'][0]) == 4:
        scanner['seller_level']['score'] = 10
        scanner['seller_level']['reputation_message'] = "BIEN. Tu reputación esta en verde claro!" 
    elif int(seller_reputation['level_id'][0]) == 5:
        scanner['seller_level']['score'] = 20
        scanner['seller_level']['reputation_message'] = "EXCELENTE. Tu reputación esta en verde oscuro!"  



     # Catalog
    if 'catalog_product_id' in item_info and item_info['catalog_product_id']:

        catalog_response = requests.get(f"https://api.mercadolibre.com/products/{item_info['catalog_product_id']}")
        catalog_info = catalog_response.json()
        try:
           cat_winner_id = catalog_info['buy_box_winner']['item_id']
        except:
           cat_winner_id = None  
        if cat_winner_id and cat_winner_id == item_id:
            scanner['catalog']['score'] = 20
            scanner['catalog']['catalog_message'] = "EXCELENTE. Estás ganando el catálogo!"
        else:
            scanner['catalog']['score'] = 10
            scanner['catalog']['catalog_message'] = "MUY BIEN. Estás participando del catálogo!"



    elif 'catalog_listing_elegible' in item_info['tags']:
        scanner['catalog']['score']  = 5 
        scanner['catalog']['catalog_message'] = "Tu producto es elegible para catálogo. Agrégalo para conseguir más ventas!" 
    elif 'catalog_product_candidate' in item_info['tags']:
        scanner['catalog']['score']  = 0 
        scanner['catalog']['catalog_message'] = "Tu publicación está muy cerca de ser elegible para catálogo. Intenta mejorar su calidad."
    else:
        scanner['catalog']['score'] = 5 
        scanner['catalog']['catalog_message']  = "Aún no existe catálogo para tu publicación."



     # Category Ranking
    item_category = item_info['category_id']
    category_ranking_response = requests.get(f"https://api.mercadolibre.com/sites/{item_site}/search?category={item_category}")
    if category_ranking_response.status_code == 200:
        category_ranking = category_ranking_response.json()['results']
        if category_ranking:
            position=0
            for result in category_ranking:
                if result['id'] == item_id:
                    break
                position+=1
                
    scanner['ranking']['position'] = position
    
    if position < 20:
        scanner['ranking']['score'] = 10
        scanner['ranking']['ranking_message'] = f"EXCELENTE. Tu publicación rankea en la posición {position+1} en su categoría."
    elif position < 50:
        scanner['ranking']['score'] = 5
        scanner['ranking']['ranking_message'] = f"BIEN. Tu publicación rankea en la posición {position+1} en su categoría."    
    else:
        scanner['ranking']['score'] = 0
        scanner['ranking']['ranking_message'] = f"MAL. Tu publicación no se encuentra entre los primeros 50 resultados de su categoría."

    # AVG Category Search Price
    prices = []
    for i in range(49):
      price = category_ranking[i]['price']
      prices.append(price)
    mean = round(np.mean(prices)) 
    scanner['ranking']['avg_price'] = f"El precio promedio de tu categoría es {mean}."



    # Total Score   
    sum_scores = sum([x['score'] for x in scanner.values()])


    output['item_id'] = item_id
    output['total_score'] = round((sum_scores / 11),1)
    output['title'] = item_info['title']
    output['image_url'] = item_info['pictures'][0]['url']
    output['price'] = item_info['price']
    output['health'] = item_info['health']
    output['date_created'] = item_info['date_created'][:10]
    output['last_updated'] = item_info['last_updated'][:10]
    output['scanner'] = scanner
    
    return output

  

st.write(run_scanner(it_cat))    

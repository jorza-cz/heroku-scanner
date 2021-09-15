import json
import requests
from datetime import datetime, timedelta
import time
import re
import numpy as np
import streamlit as st

BLACKLIST = [r'\d+\%', r'\d+\s\%', 'nuevo', 'descuento', 'usado', 'oferta', 'liquidaci', '%off', 'off!', 'envio', 'envío', 'gratis', 'llega', 'hoy', 'cuotas', 'sin interes', 'talle']

HEADERS = {
  'x-caller-id': '593253618',
  'Content-Type': 'application/json'
}

item_id = st.text_input("item_id", "MLA900378644")

def check_bad_words(blacklist, title):
    title = title.lower()
    for pattern in blacklist:
        if re.search(pattern, title):
            return 0
    return 2

def listing_by_site(site_id, type):
    if site_id in ['MPE', 'MLV', 'MLU']:
        listings = {'free':'Gratuita', 'bronze':'Clásica', 'gold_special' : 'Premium'}
    else:
        listings = {'free':'Gratuita', 'gold_special':'Clásica', 'gold_pro' : 'Premium'}
    return listings[type]
    
    
def datetime_difference(string1, string2):
    return (datetime.strptime(string2[:19], '%Y-%m-%dT%H:%M:%S') - datetime.strptime(string1[:19], '%Y-%m-%dT%H:%M:%S')).seconds

def answer_score(minutes):
    if minutes <= 2:
        return 10
    elif minutes <= 5:
        return 8
    elif minutes <= 10:
        return 6
    else:
        return 0

def run_scanner(item_id):
    output = dict()
    scanner = dict()

    item_response = requests.get(f"https://api.mercadolibre.com/items/{item_id}")
    item_info = item_response.json()

    for name in ['title', 'image', 'specs','category', 'shipping', 'listing_type', 'answers', 'seller_level', 'catalog', 'ranking']:
        scanner[name] = {'score': 5, 'message': ''}

    # Check title
    item_title = item_info['title'].lower()
    item_site = item_info['site_id']

    # Check brand and model
    brand = next((attr for attr in item_info['attributes'] if attr['id'] == 'BRAND'), None)
    if brand:
        brand_name = brand['value_name'].lower()
        brand_score = 2
        for word in brand_name.split(' '):
            if not re.search(word, item_title):
                brand_score = 0
                break
        brand_message = f'El título de la publicación no contiene el nombre de la marca "{brand_name}".' if (brand_score == 0) else ''
    else:
        brand_score = 1
        brand_message = ''

    model = next((attr for attr in item_info['attributes'] if attr['id'] == 'MODEL'), None)
    if model:
        model_name = model['value_name'].lower()
        model_score = 2
        for word in model_name.split(' '):
            if not re.search(word, item_title):
                model_score = 0
                break
        model_message = f'El título de la publicación no contiene el nombre del modelo "{model_name}".' if (brand_score == 0) else ''
    else:
        model_score = 1
        model_message = ''

    # Check blacklist words in title
    bar_words_score = check_bad_words(BLACKLIST, item_title)
    title_message = 'El título contiene términos irrelevantes.' if (bar_words_score == 0) else ''

    scanner['title']['score'] = 4 + bar_words_score + brand_score + model_score
    scanner['title']['message'] = "El título es correcto." if (scanner['title']['score'] == 10) else ' '.join([title_message, brand_message, model_message])


    # Check image quality
    picture_score = 1 if ('good_quality_picture' in item_info['tags']) else 0
    thumbnail_score = 1 if ('good_quality_thumbnail' in item_info['tags']) else 0
    scanner['image']['score'] = (picture_score + thumbnail_score)*5
    if picture_score and thumbnail_score:
        message = "Las imágenes de tu publicación son muy buenas."
    elif picture_score:
        message = "La imagen de portada de tu publicación no es de buena calidad. Intenta mejorarla para atraer más compradores!."
    elif thumbnail_score:
        message = "Las imágenes de tu publicación no son de buena calidad. Intenta mejorarlas para atraer más compradores!."
    else:
        message = "Intenta mejorar las imágenes de portada y principales de tu publicación para atraer más compradores."
    scanner['image']['message'] = message

    # Technical Specs
    if 'incomplete_technical_specs' in item_info['tags']:
        scanner['specs']['score'] = 6
        scanner['specs']['message'] = "Mejora tu publicación completando su ficha técnica." 
    else:
        scanner['specs']['score'] = 10
        scanner['specs']['message'] = "Tu publicación posee una ficha técnica completa." 

    # Category
    pred_category_response = requests.get(f"https://api.mercadolibre.com/sites/{item_site}/domain_discovery/search?q={item_title}")
    if pred_category_response.status_code == 200:
        pred_category = pred_category_response.json()
        if pred_category and 'category_id' in pred_category[0]:
            if (pred_category[0]['category_id'] == item_info['category_id']):
                scanner['category']['score'] = 10
                scanner['category']['message'] = "Tu producto está publicado en la categoría correcta."
            elif 'category_name' in pred_category[0]:
                new_category = pred_category[0]['category_name']
                scanner['category']['score'] = 6
                scanner['category']['message'] = f'Tal vez debas publicar tu producto en la categoría "{new_category}".'
        else:
            scanner['category']['score'] = 5
            scanner['category']['message'] = f'No pudimos determinar la categoría adecuada para tu producto.'

    # Shipping
    if 'shipping' in item_info:
        if 'me2' in item_info['shipping']['mode']:
            if 'free_shipping' in item_info['shipping'] and item_info['shipping']['free_shipping']:
                scanner['shipping']['score'] = 10 
                scanner['shipping']['message'] = "Ofreces el mejor servicio de envío."
            else:
                scanner['shipping']['score'] = 7 
                scanner['shipping']['message'] = "Podrías ofrecer envíos gratis para mejorar tu publicación."
        else:
            scanner['shipping']['score'] = 2
            scanner['shipping']['message'] = "Podrías ofrecer Mercado Envíos para mejorar tu publicación."

    # Listing type
    listing_type = listing_by_site(item_site, item_info['listing_type_id'])
    if listing_type == 'Premium':
        scanner['listing_type']['score'] = 10
        scanner['listing_type']['message'] = "Tu publicación es de tipo Premium."
    if listing_type == 'Clásica':
        scanner['listing_type']['score'] = 7
        scanner['listing_type']['message'] = "Tu publicación es de tipo Clásica. Intenta mejorarla a Premium."
    else:
        scanner['listing_type']['score'] = 4
        scanner['listing_type']['message'] = "Tu publicación es de tipo Gratuita. Intenta mejorarla a Clásica o Premium."


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
        scanner['seller_level']['level'] = 0

    scanner['seller_level']['score'] = 2*scanner['seller_level']['level']

    if scanner['seller_level']['level'] > 3:
        scanner['seller_level']['message'] = "Tu reputación es muy buena. Sigue así!"
    else:    
        scanner['seller_level']['message'] = "Tu reputación te está haciendo perder visibilidad."



    # Catalog
    if 'catalog_product_id' in item_info and item_info['catalog_product_id']:
        scanner['catalog']['score'] = 10
        scanner['catalog']['message'] = "Tu publicación está en catálogo. Excelente!"
    elif 'catalog_listing_elegible' in item_info['tags']:
        scanner['catalog']['score']  = 8 
        scanner['catalog']['message'] = "Tu producto es elegible para catálogo. Agrégalo para conseguir más ventas!" 
    elif 'catalog_product_candidate' in item_info['tags']:
        scanner['catalog']['score']  = 6 
        scanner['catalog']['message'] = "Tu publicación está muy cerca de ser elegible para catálogo. Intenta mejorar su calidad."
    else:
        scanner['catalog']['score'] = 2 
        scanner['catalog']['message']  = "Si mejoras tu publicación podrías participar de catálogo y conseguir más ventas."

    # Category ranking
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
    scanner['ranking']['score'] = (10 - position // 5)
    if position < 50:
        scanner['ranking']['message'] = f"Tu publicación rankea en la posición {position+1} en su categoría."
    else:
        scanner['ranking']['message'] = f"Tu publicación no se encuentra entre los primeros 50 resultados de su categoría."



    # Total Score
    if 'health' in 'item_info':
        total_score = (sum([x['score'] for x in scanner.values()]) + item_info['health']*100)/40
    else:
        total_score = sum([x['score'] for x in scanner.values()]) / 20


    output['total_score'] = round(total_score,1)
    output['title'] = item_info['title']
    output['image_url'] = item_info['pictures'][0]['url']
    output['price'] = item_info['price']
    output['scanner'] = scanner

    return output

st.write(run_scanner(item_id))    
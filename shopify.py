import sys
import csv
import json
import time
import urllib.request
from urllib.error import HTTPError
from optparse import OptionParser


USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'


def get_page(url, page, collection_handle=None):
    full_url = url
    if collection_handle:
        full_url += '/collections/{}'.format(collection_handle)
    full_url += '/products.json'
    req = urllib.request.Request(
        full_url + '?page={}'.format(page),
        data=None,
        headers={
            'User-Agent': USER_AGENT
        }
    )
    while True:
        try:
            data = urllib.request.urlopen(req).read()
            break
        except HTTPError:
            print('Blocked! Sleeping...')
            time.sleep(180)
            print('Retrying')
        
    products = json.loads(data.decode())['products']
    return products


def get_page_collections(url):
    full_url = url + '/collections.json'
    page = 1
    while True:
        req = urllib.request.Request(
            full_url + '?limit=50&page={}'.format(page),
            data=None,
            headers={
                'User-Agent': USER_AGENT
            }
        )
        while True:
            try:
                data = urllib.request.urlopen(req).read()
                break
            except HTTPError:
                print('Blocked! Sleeping...')
                time.sleep(180)
                print('Retrying')

        cols = json.loads(data.decode())['collections']
        if not cols:
            break
        for col in cols:
            yield col
        page += 1


def check_shopify(url):
    try:
        get_page(url, 1)
        return True
    except Exception:
        return False


def fix_url(url):
    fixed_url = url.strip()
    if not fixed_url.startswith('http://') and \
       not fixed_url.startswith('https://'):
        fixed_url = 'https://' + fixed_url

    return fixed_url.rstrip('/')


def extract_products_collection(url, col):
    page = 1
    products = get_page(url, page, col)
    while products:
        for product in products:
            title = product['title']
            product_type = product['product_type']
            product_url = url + '/products/' + product['handle']
            product_handle = product['handle']

            def get_image(variant_id):
                images = product['images']
                for i in images:
                    k = [str(v) for v in i['variant_ids']]
                    if str(variant_id) in k:
                        return i['src']

                return ''

            for i, variant in enumerate(product['variants']):
                
                sku = variant['sku']
                main_image_src = ''
                if product['images']:
                    main_image_src = product['images'][0]['src']

                image_src = get_image(variant['id']) or main_image_src
                stock = 'Yes'
                if not variant['available']:
                    stock = 'No'
                row = variant
                row.update(product)

                rowProps = {'sku': sku, 
                        'product_type': product['product_type'],
                        'title' : product['title'],
                        'title' : product['title'],
                        'product_type' : product['product_type'],
                        'product_url' : url + '/products/' + product['handle'],
                        'product_handle' : product['handle'],
                        'option1_value' : variant['option1'] or '',
                        'price' : variant['price'],
                        'compare_at_price' : variant['compare_at_price'],
                        'option2_value' : variant['option2'] or '',
                        'option3_value' : variant['option3'] or '',
                        'grams' : variant['grams'] or '',
                        'requires_shipping' : variant['requires_shipping'] or 'TRUE',
                        'stock': stock,
                        # 'body': str(product['body_html']),
                        'variant_id': product_handle + str(variant['id']),
                        'product_url': product_url,
                        'image_src': image_src
                        }
                row.update(rowProps)
                for k in row:
                    row[k] = str(str(row[k]).strip()) if row[k] else ''
                yield row

        page += 1
        products = get_page(url, page, col)


def extract_products(url, path, collections=None):
    import os
    if os.path.exists(path):
        os.remove(path)
    with open(path, 'w', encoding="utf-8", newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Handle',	'Title',	'Body (HTML)',	'Vendor',	'Standardized Product Type',	'Custom Product Type',	'Tags',	'Published',	'Option1 Name',	'Option1 Value',	'Option2 Name',	'Option2 Value',	'Option3 Name',	'Option3 Value',	'Variant SKU',	'Variant Grams',	'Variant Inventory Tracker',	'Variant Inventory Qty',	'Variant Inventory Policy',	'Variant Fulfillment Service',	'Variant Price',	'Variant Compare At Price',	'Variant Requires Shipping',	'Variant Taxable',	'Variant Barcode',	'Image Src',	'Image Position',	'Image Alt Text',	'Gift Card',	'SEO Title',	'SEO Description',	'Google Shopping / Google Product Category',	'Google Shopping / Gender',	'Google Shopping / Age Group',	'Google Shopping / MPN',	'Google Shopping / AdWords Grouping',	'Google Shopping / AdWords Labels',	'Google Shopping / Condition',	'Google Shopping / Custom Product',	'Google Shopping / Custom Label 0',	'Google Shopping / Custom Label 1',	'Google Shopping / Custom Label 2',	'Google Shopping / Custom Label 3',	'Google Shopping / Custom Label 4',	'Variant Image',	'Variant Weight Unit',	'Variant Tax Code',	'Cost per item',	'Price / International',	'Compare At Price / International',	'Status'])
        seen_variants = set()
        products =[]
        for col in get_page_collections(url):
            if collections and col['handle'] not in collections:
                continue
            col_handle = col['handle']
            co_title = col['title']
            print('fetching Collection: ' + col_handle)

            for product in extract_products_collection(url, col_handle):
                variant_id = product['variant_id']
                # if variant_id in seen_variants:
                #     continue
                seen_variants.add(variant_id)
                option_name = ''
                tags = ''
                print('product: ' + product['product_handle'])
                try:
                    product['options']= json.loads(product['options'].replace("\'", "\""))
                    option_name = product['options'][0]['name']
                    # print(type(tags))
                    # print(tags)
                except Exception as e:
                    print('error in options string: ' + product['options'])
                    print(e)
                    option_name='color'
                    pass
                try:
                    tags = ','.join(json.loads(product['tags'].replace("\'", "\"")))
                    # print('tags: '+tags)
                except Exception as e:

                    print(e)
 
 
                # print(product['featured_image'].replace("\'", "\""))
                # product['featured_image']= json.loads(product['featured_image'].replace("\'", "\""))
                # del product['body_html']
                writer.writerow([
                    product['product_handle'],
                    product['title'],
                    product['body_html'],#Body html
                    product['vendor'] or '', #Vendor
                    '',#'Standardized Product Type',
                    product['product_type'],#	'Custom Product Type',
                    tags,# Tags
                    'TRUE',	# 'Published',
                    option_name,#	'Option1 Name',
                    product['option1_value'],#	'Option1 Value',	
                    '', #option2 Name
                    product['option2_value'],#	'Option2 Value',	
                    '', #option3 Name
                    product['option3_value'],#	'Option3 Value',	
                    product['sku'],    #'Variant SKU'	,
                    product['grams'],#  'Variant Grams'	,
                    '',    #    'Variant Inventory Tracker'	,
                    '100',    #    'Variant Inventory Qty'	,
                    'deny',    #    'Variant Inventory Policy'	,
                    'manual',    # 'Variant Fulfillment Service'	,
                     product['price'],   #  'Variant Price'	,
                     product['compare_at_price'],   #    'Variant Compare At Price'	,
                     product['requires_shipping'],   # 'Variant Requires Shipping'	,
                     'FALSE',#product['taxable'],   #    'Variant Taxable'	,
                     '',   #  'Variant Barcode'	,
                       product['image_src'], #  'Image Src'	,
                    '',#   product['featured_image']['position'],  #    'Image Position'	,
                    '',#   product['featured_image']['alt'],  #   'Image Alt Text'	,
                      'FALSE',  #   'Gift Card'	,
                     '',   #    'SEO Title'	,
                     '',   #    'SEO Description'	,
                     col_handle,   #  'Google Shopping / Google Product Category'	,
                      '',  #    'Google Shopping / Gender'	,
                     '',   # 'Google Shopping / Age Group'	,
                     '',   #  'Google Shopping / MPN'	,
                      '',  #    'Google Shopping / AdWords Grouping'	,
                     '',   #   'Google Shopping / AdWords Labels'	,
                      '',  # 'Google Shopping / Condition'	,
                      '',  #  'Google Shopping / Custom Product'	,
                      '',  # 'Google Shopping / Custom Label 0'	,
                      '',  # 'Google Shopping / Custom Label 1'	,
                      '',  # 'Google Shopping / Custom Label 2'	,
                      '',  # 'Google Shopping / Custom Label 3'	,
                       '', # 'Google Shopping / Custom Label 4'	,
                      product['image_src'],  # 'Variant Image'	,
                      '',  #    'Variant Weight Unit'	,
                     '',   #  'Variant Tax Code'	,
                      '',  # 'Cost per item'	,
                      '',  #    'Price / International'	,
                      '',  #    'Compare At Price / International'	,
                      'ACTIVE'# 'Status'	,
                ])

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("--list-collections", dest="list_collections",
                      action="store_true",
                      help="List collections in the site")
    parser.add_option("--collections", "-c", dest="collections",
                      default="",
                      help="Download products only from the given collections (comma separated)")
    (options, args) = parser.parse_args()
    if len(args) > 0:
        url = fix_url(args[0])
        if options.list_collections:
            for col in get_page_collections(url):
                print(col['handle'])
        else:
            collections = []
            if options.collections:
                collections = options.collections.split(',')
            extract_products(url, 'products.csv', collections)

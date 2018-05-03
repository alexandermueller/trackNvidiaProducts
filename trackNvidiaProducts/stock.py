#!/usr/bin/env python

############################
# Alexander Mueller - 2018 #
# Stock.py handles a bunch #
# of different information #
# retreival tasks, like    #
# getting product stock    #
# levels and related info. #
############################

import urllib, json
import sys
import time 
import smtplib

currencyMap = {
               'de_de' : 'EUR',
               'en_us' : 'USD',
               'en_gb' : 'GBP',
               'fr_fr' : 'EUR',
               'nl_nl' : 'EUR'
              }

# These are ids that the api happened to not return for some reason, 
# but still need to be tracked when calling the api. 
specialIdsMap = {
                 'de_de' : ',5136449400,5136449100',
                 'fr_fr' : ',5136449500,5136449200', 
                 'en_gb' : ',5136449600,5136449300',
                 'en_us' : ',5094274700,5144751300',
                 'nl_nl' : ',5062286200,5136374600,5148081600,5148081500'                        
                }

apiKey   = '9485fa7b159e42edb08a83bde0d83dia'
priceKey = 'Price'
stockKey = 'Left in Stock'
availKey = 'Expected Restock Date'

## prettyPrint
#
# Takes in a dictionary with a string -> array of strings mapping.
# The arrays must all be of equal size, as each element represents
# the corresponding value of that item's attribute (the dictionary key.)
#
# eg: info = {
#             'Price' : ['12 EUR', '123 EUR', '10 EUR'],
#             'Stock' : ['12', 23, 0],
#             'Name'  : ['Cheap', 'Expensive', 'Popular']
#            }
# So the first item is worth 12 Euro, has 12 left, and is called Cheap.
#
# prettyPrint takes each item and prints the attributes out on a single 
# line, while aligning all the attribute values vertically to make it easy
# to read. 
##

def prettyPrint(info):
    maxLengths = {}
    itemCount  = len(info[info.keys()[0]])

    for key in info.keys():
        maxLen = 0
        
        for item in info[key]:
            if maxLen < len(item):
                maxLen = len(item)

        maxLengths[key] = maxLen

    for i in xrange(0, itemCount):
        print str(i + 1) + ') ' + ' | '.join([key + ' : ' + ' ' * (maxLengths[key] - len(info[key][i])) + info[key][i] for key in info.keys()]) 

## printItemInfo
# 
# Accepts a list of products and a locale,
# and compiles useful information so that 
# it's easy to print out to the terminal.
##

def printItemInfo(items, locale):
    if len(items) > 0:
        print
    	print '>' * 26 + ' Prices and stock for: ' + locale.split('_')[1].upper() + ' ' + '<' * 26
        print '--> Products:'
        
        i    = 1
        seen = [] 

        for item in items:
            if item['sku'] not in seen:
                seen.append(item['sku'])
                print str(i) + ') ' + item['displayName']
                i += 1

        print 
        print '--> Product Information:'

        i      = 1
        prices = []
        stocks = []
        avails = []
        seen   = []

        for item in items:
            inventory = item['inventoryStatus']
            pricing   = item['pricing']['listPrice']

            # do something in the future with sale price maybe...?

            if 'availableQuantity' in inventory.keys() and item['sku'] not in seen:
                seen.append(item['sku'])
                prices.append('%i %s' % (pricing['value'], pricing['currency']))
                stocks.append(str(inventory['availableQuantity']))
                avails.append(inventory['expectedInStockDate'].split('T')[0])
                i += 1

        prettyPrint({priceKey : prices, stockKey : stocks, availKey : avails})

## getAllProductInformation
#
# Calls the Nvidia storefront api that is managed by digitalrivier,
# and retreives all items it can for each locale. First, it does a 
# call to retrieve as many product ids it can, which doesn't end
# up returning the actual information but the product ids for each
# item instead. This allows for a more broad item coverage, so that 
# we don't need to hardcode so many ourselves, but it seems that it
# is still necessary for certain items. Next, it loops through all the
# products, and filters them out based on their names, so that we don't 
# get undesired products, and then calls the api with the filtered ids.
# This returns the actual product information, and then passes that on to 
# be organized and printed out.
##

def getAllProductInformation():
    print '-- Nvidia Product Prices & Stock Levels --'

    for locale in currencyMap.keys():
        currency   = currencyMap[locale]
        apiUrl     = 'https://api.digitalriver.com/v1/shoppers/me/products?format=json&expand=all&locale=%s&apiKey=%s&currency=%s' % (locale, apiKey, currency) 
        response   = urllib.urlopen(apiUrl)
        data       = json.loads(response.read())

        if 'products' in data.keys() and 'product' in data['products'].keys() and data['products']['totalResults'] > 0: 
            items      = data['products']['product']        
            productIds = []
            
            for item in items:
                name = item['displayName'].lower()

                if 'gtx' in name or 'titan' in name or 'collector' in name:
                    productIds.append(str(item['id'])) 

            newURL   = apiUrl + '&productId=' + ','.join(productIds) + specialIdsMap[locale]
            itemResp = urllib.urlopen(newURL)
            itemData = json.loads(itemResp.read())
            items    = itemData['products']['product']

            printItemInfo(items, locale)

## inStock
#
# Accepts a locale, and the digital river api product id of the desired item.
# Using this information, it checks the stock levels of the item, and returns
# True only if th stock levels are above 0.
##

def inStock(productId, locale):
    currency = currencyMap[locale]
    apiUrl   = 'https://api.digitalriver.com/v1/shoppers/me/products?format=json&expand=all&locale=%s&apiKey=%s&currency=%s&productId=%s' % (locale, apiKey, currency, productId) 
    response = urllib.urlopen(apiUrl)
    data     = json.loads(response.read())

    if 'products' in data.keys() and 'product' in data['products'].keys() and data['products']['totalResults'] > 0: 
        item = data['products']['product'][0]
        return item['inventoryStatus']['availableQuantity'] > 0

    return False


# def sendEmail():
#     server = smtplib.SMTP('smtp.gmail.com', 587)
#     server.starttls()
#     server.login("email address", "password")
     
#     msg = "message, this doesn't really work anyway, the email will be empty"
#     server.sendmail("from", "to", msg)
#     server.quit()

## notifyWhenInStock
#
# Takes a locale and productId, and loops
# forever until the product at that locale 
# is in stock. When it is in stock, it notifies
# the user and terminates.
##

def notifyWhenInStock(productId, locale):
    print 'Checking Stock...'
    
    i = 1

    while not inStock(productId, locale):
        print '--> Check #' + str(i)
        time.sleep(15)
        i += 1

    print 'Hell, Yeah!'

def main(argc, argv):
    if argc == 3 and argv[0] == '-notify':
        notifyWhenInStock(argv[1], argv[2])
    else:
        getAllProductInformation()
        print
  
if __name__ == '__main__':
   main(len(sys.argv) - 1, sys.argv[1:])

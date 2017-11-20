from __future__ import division
import requests
import json
import sys
import time

try:
   input = raw_input
except NameError:
   pass

def downloadFile( requestHeaders, packageDelivery, isDirectDownload ):
    total_length = int(packageDelivery['FileSizeBytes'])
    packageName=packageDelivery['Name']
    
    print("Download: " + packageName + ' (' + str(total_length) + ' bytes )')
    requestUrl = 'https://hosted.datascopeapi.reuters.com/RestApi/v1/StandardExtractions/UserPackageDeliveries(\''+packageDelivery['PackageDeliveryId']+'\')/$value'
    print("GET " + requestUrl)
    #Add additional header, "X-Direct-Download:true", to download file directly from Amazon Web Service.
    if (isDirectDownload):
        requestHeaders["X-Direct-Download"] = "true"
    r = requests.get(requestUrl,headers=requestHeaders,stream=True)
    
    dl = 0
    chunk_size = 1024
    t1 = time.time()
    with open(packageName, 'wb') as fd:
       for data in r.raw.stream(chunk_size,decode_content=False):
           # write chunked data to file
           fd.write(data)

           # track the download progress and disply to console
           dl += len(data)
           done = int(50 * dl / total_length)
           percent = (dl / total_length) * 100
           sys.stdout.write("\r[%s%s]%d%%" % ('=' * done, ' ' * (50-done),percent ))   
           sys.stdout.flush()
    t2 = time.time()
    sys.stdout.write("\nCompleted download %s file within %d second" % (packageName,t2-t1))
    return



def listUserPackageDeliveries( deliveryList ):
   print("PackageDeliveryId  : Name (file size in Bytes)\n")
   for userPackageDelivery in deliveryList:
       print(str(userPackageDelivery["PackageDeliveryId"]) + " : " + userPackageDelivery["Name"] + "(" + str(userPackageDelivery["FileSizeBytes"]) +" bytes)")
   return

def main():
    #Step 1: send an authentication request to retrieve token
    requestUrl = "https://hosted.datascopeapi.reuters.com/RestApi/v1/Authentication/RequestToken"

    requestHeaders={
        "Prefer":"respond-async",
        "Content-Type":"application/json"
        }

    requestBody={
        "Credentials": {
        "Username": "<DSS username>",
        "Password": "<DSS password>"
      }
    }

    response = requests.post(requestUrl, json=requestBody,headers=requestHeaders)

    if response.status_code == 200 :
        jsonResponse = json.loads(response.text.encode('ascii', 'ignore'))
        token = jsonResponse["value"]
        print ('Authentication token (valid 24 hours):')
        print (token)
    else:
        print ('Please replace myUserName and myPassword with valid credentials, then repeat the request')
        return;

    # Create HTTP header with received token.
    requestHeaders={
        "Prefer":"respond-async",
        "Content-Type":"application/json",
        "Authorization": "token " + token        
    }
    

    #Step 2: Access VBD file’s information
    menu = input('1: Get list of UserDeliveryPackageId by a specific package \
                      \n2: Get List of UserDeliveryPackageId by a specific date \
                      \nEnter a menu: ')

    #Step 2-a:Get UserPackageDeliveries By Package Id
    if (menu == '1'):
        #Step 2.1-a: Get list of permitted Packages Id
        requestUrl='https://hosted.datascopeapi.reuters.com/RestApi/v1/StandardExtractions/UserPackages'
        print ("GET " + requestUrl)
        response = requests.get(requestUrl, headers=requestHeaders)

        if response.status_code == 200:
            print ("PackageId          : Package Name\n")
            jsonResponse = json.loads(response.text.encode('ascii','ignore'))
            for package in jsonResponse["value"]:
                print(str(package["PackageId"]) + " : " + package["PackageName"])

        #Step 2.2-a: Get list of UserPackageDeliveries by selected Package Id
        packageId = input('Enter package Id: ')
        requestUrl='https://hosted.datascopeapi.reuters.com/RestApi/v1/StandardExtractions/UserPackageDeliveryGetUserPackageDeliveriesByPackageId(PackageId=\''+packageId+'\')'
        print ("GET " + requestUrl)
        response = requests.get(requestUrl, headers=requestHeaders)

    #Step 2-b: Get UserPackageDeliveries By Date Range
    elif (menu == '2'):
        #Step 2.1-b: Get Subscription Id for "TRTH Venue by Day"
        requestUrl='https://hosted.datascopeapi.reuters.com/RestApi/v1/StandardExtractions/Subscriptions'
        print ("GET " + requestUrl)
        response = requests.get(requestUrl, headers=requestHeaders)

        #Find subscription id for "TRTH Venue by Day"
        subscriptionId=''
        if response.status_code == 200:
            jsonResponse = json.loads(response.text.encode('ascii','ignore'))
            
            for subscription in jsonResponse['value']:
                if (subscription['Name'] == 'TRTH Venue by Day'):
                    subscriptionId = subscription['SubscriptionId']
                    print("SubscriptionId for TRTH Venue by Day is " + subscriptionId)
            if (subscriptionId == ''):
                print("Cannot find TRTH Venue by Day subscription")
                return;

        #Step 2.2-b: Get list of UserPackageDeliveries by selected Date Range. In this example, the range is only one day
        date = input('Enter date to get VBD file within past 30 days period (Date format example: 2017-10-23) :')
        requestUrl='https://hosted.datascopeapi.reuters.com/RestApi/v1/StandardExtractions/UserPackageDeliveryGetUserPackageDeliveriesByDateRange(SubscriptionId=\''+subscriptionId+'\',FromDate=' + date + 'T00:00:00.000Z,ToDate=' + date +'T23:59:59.999Z)'
        print ("GET " + requestUrl)
        response = requests.get(requestUrl, headers=requestHeaders)
    else:
        print ("Select invalid menu")
        return

    #Create list of UserPackageDeliveries in local to store PackageDeliveries
    userPackageDeliveryList = list()
    jsonResponse = json.loads(response.text.encode('ascii','ignore'))
    
    if response.status_code == 200:
        updateList = jsonResponse["value"]
        #Store list of package deliveries received from the fist page in cache
        userPackageDeliveryList.extend(updateList)
        listUserPackageDeliveries (updateList)

        if (updateList):
            # Store NextLink url for requesting next page.
            if jsonResponse['@odata.nextlink'] != '':
                nextlink = jsonResponse['@odata.nextlink']
                print("\n@odata.nextlink: " + nextlink)
        else:
            # Empty result is returned. This can be assumed that the selected date is incorrect.
            print("Empty list\n")
            return;
    else:
        print(jsonResponse["error"])
        return;

    #Step 3: Download VBD files or load next page of UserPackageDeliveryFile list
    while True:
        command = input('\nEnter one of the following command \
                            \n\'n\' to request next page \
                            \n\'d <User package Id>\' to download the selected file from DSS \
                            \n\'x <User package Id>\' to download the selected file directly from Amazon Web Service \
                            \n : ')

        # Request next page of PackageDeliveries list
        if command == 'n':
            if nextlink != '':
                print ("GET " + nextlink)
                response = requests.get(nextlink, headers=requestHeaders)
                jsonResponse = json.loads(response.text.encode('ascii','ignore'))
                updateList = jsonResponse["value"]
                #Store list of package deliveries received from the next page in cache
                userPackageDeliveryList.extend(updateList)
                listUserPackageDeliveries(updateList)
                if jsonResponse['@odata.nextlink'] != '':
                    nextlink = jsonResponse.get('@odata.nextlink','')
                    print("\n@odata.nextlink: " + nextlink)
            else:
                print("There is no NextLink. This is an end of pages.")
                
        else:
            # Download VBD files for selected PackageDeliveryId.
            args = command.split()
            if (len(args)==2 and (args[0]=='d' or args[0]=='x')):
                # Retrieve information of selected PackageDeliveryId stored in cache.
                filteredList = [x for x in userPackageDeliveryList if x['PackageDeliveryId'] == args[1]]
                if (len(filteredList)!=0):
                    # Download a file from DSS server
                    if (args[0] =='d'):
                        downloadFile(requestHeaders,filteredList[0],False)
                    # Download a file from Amazon Web Service
                    elif (args[0] == 'x'):
                        downloadFile(requestHeaders,filteredList[0],True)
                else:
                    print('No PackageDeliveryId found')

if __name__ == "__main__":
    main()



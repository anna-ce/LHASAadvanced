#!/usr/bin/env python
#
# Created on 9/27/2012 Pat Cappelaere - Vightel Corporation
#
# Requirements:
#
# Convert DB to geojson
#
import os, sys, inspect
import array
from datetime import date
import argparse
import urllib


if __name__ == '__main__':

lat = 54.549391	
lon = -3.587473

http://api.geonames.org/findNearbyJSON?lat=54.549391&lng=-3.587473&username=cappelaere
{

    "geonames": [
        {
            "countryId": "2635167",
            "adminCode1": "ENG",
            "countryName": "United Kingdom",
            "fclName": "city, village,...",
            "countryCode": "GB",
            "lng": "-3.58412",
            "fcodeName": "populated place",
            "distance": "0.22213",
            "toponymName": "Whitehaven",
            "fcl": "P",
            "name": "Whitehaven",
            "fcode": "PPL",
            "geonameId": 2634096,
            "lat": "54.54897",
            "adminName1": "England",
            "population": 24803
        }
    ]

}

http://api.geonames.org/findNearbyPlaceNameJSON?lat=54.549391&lng=-3.587473&radius=50&style=FULL&cities=cities5000&maxrows=10&username=cappelaere
{

    "geonames": [
        {
            "adminCode3": "16UE",
            "adminCode2": "C9",
            "alternateNames": [
                {
                    "name": "Уайтхейвън",
                    "lang": "bg"
                },
                {
                    "name": "http://en.wikipedia.org/wiki/Whitehaven",
                    "lang": "link"
                }
            ],
            "countryName": "United Kingdom",
            "adminCode1": "ENG",
            "lng": "-3.58412",
            "adminName2": "Cumbria",
            "fcodeName": "populated place",
            "adminName3": "Copeland District",
            "distance": "0.22213",
            "timezone": {
                "dstOffset": 1,
                "gmtOffset": 0,
                "timeZoneId": "Europe/London"
            },
            "adminName4": "",
            "adminName5": "",
            "name": "Whitehaven",
            "fcode": "PPL",
            "geonameId": 2634096,
            "lat": "54.54897",
            "population": 24803,
            "adminName1": "England",
            "adminId1": "6269131",
            "countryId": "2635167",
            "fclName": "city, village,...",
            "elevation": 0,
            "countryCode": "GB",
            "adminId3": "7290665",
            "adminId2": "2651712",
            "toponymName": "Whitehaven",
            "fcl": "P",
            "continentCode": "EU"
        },
        {
            "adminCode3": "16UE",
            "adminCode2": "C9",
            "alternateNames": [
                {
                    "name": "http://en.wikipedia.org/wiki/Cleator_Moor",
                    "lang": "link"
                }
            ],
            "countryName": "United Kingdom",
            "adminCode1": "ENG",
            "lng": "-3.5159",
            "adminName2": "Cumbria",
            "fcodeName": "populated place",
            "adminName3": "Copeland District",
            "distance": "5.58127",
            "timezone": {
                "dstOffset": 1,
                "gmtOffset": 0,
                "timeZoneId": "Europe/London"
            },
            "adminName4": "",
            "adminName5": "",
            "name": "Cleator Moor",
            "fcode": "PPL",
            "geonameId": 2652891,
            "lat": "54.52143",
            "population": 6507,
            "adminName1": "England",
            "adminId1": "6269131",
            "countryId": "2635167",
            "fclName": "city, village,...",
            "elevation": 0,
            "countryCode": "GB",
            "adminId3": "7290665",
            "adminId2": "2651712",
            "toponymName": "Cleator Moor",
            "fcl": "P",
            "continentCode": "EU"
        },
        {
            "adminCode3": "16UE",
            "adminCode2": "C9",
            "alternateNames": [
                {
                    "name": "http://en.wikipedia.org/wiki/Egremont%2C_Cumbria",
                    "lang": "link"
                }
            ],
            "countryName": "United Kingdom",
            "adminCode1": "ENG",
            "lng": "-3.52756",
            "adminName2": "Cumbria",
            "fcodeName": "populated place",
            "adminName3": "Copeland District",
            "distance": "8.70257",
            "timezone": {
                "dstOffset": 1,
                "gmtOffset": 0,
                "timeZoneId": "Europe/London"
            },
            "adminName4": "",
            "adminName5": "",
            "name": "Egremont",
            "fcode": "PPL",
            "geonameId": 2650174,
            "lat": "54.47941",
            "population": 6130,
            "adminName1": "England",
            "adminId1": "6269131",
            "countryId": "2635167",
            "fclName": "city, village,...",
            "elevation": 0,
            "countryCode": "GB",
            "adminId3": "7290665",
            "adminId2": "2651712",
            "toponymName": "Egremont",
            "fcl": "P",
            "continentCode": "EU"
        },
        {
            "adminCode3": "16UB",
            "adminCode2": "C9",
            "alternateNames": [
                {
                    "name": "Уъркингтън",
                    "lang": "bg"
                },
                {
                    "name": "http://en.wikipedia.org/wiki/Workington",
                    "lang": "link"
                }
            ],
            "countryName": "United Kingdom",
            "adminCode1": "ENG",
            "lng": "-3.54413",
            "adminName2": "Cumbria",
            "fcodeName": "populated place",
            "adminName3": "Allerdale District",
            "distance": "10.73656",
            "timezone": {
                "dstOffset": 1,
                "gmtOffset": 0,
                "timeZoneId": "Europe/London"
            },
            "adminName4": "",
            "adminName5": "",
            "name": "Workington",
            "fcode": "PPL",
            "geonameId": 2633553,
            "lat": "54.6425",
            "population": 20618,
            "adminName1": "England",
            "adminId1": "6269131",
            "countryId": "2635167",
            "fclName": "city, village,...",
            "elevation": 0,
            "countryCode": "GB",
            "adminId3": "7290662",
            "adminId2": "2651712",
            "toponymName": "Workington",
            "fcl": "P",
            "continentCode": "EU"
        },
        {
            "adminCode3": "16UB",
            "adminCode2": "C9",
            "alternateNames": [
                {
                    "name": "http://en.wikipedia.org/wiki/Cockermouth",
                    "lang": "link"
                }
            ],
            "countryName": "United Kingdom",
            "adminCode1": "ENG",
            "lng": "-3.36086",
            "adminName2": "Cumbria",
            "fcodeName": "populated place",
            "adminName3": "Allerdale District",
            "distance": "19.28285",
            "timezone": {
                "dstOffset": 1,
                "gmtOffset": 0,
                "timeZoneId": "Europe/London"
            },
            "adminName4": "",
            "adminName5": "",
            "name": "Cockermouth",
            "fcode": "PPL",
            "geonameId": 2652676,
            "lat": "54.66209",
            "population": 7612,
            "adminName1": "England",
            "adminId1": "6269131",
            "countryId": "2635167",
            "fclName": "city, village,...",
            "elevation": 0,
            "countryCode": "GB",
            "adminId3": "7290662",
            "adminId2": "2651712",
            "toponymName": "Cockermouth",
            "fcl": "P",
            "continentCode": "EU"
        },
        {
            "adminCode3": "16UB",
            "adminCode2": "C9",
            "alternateNames": [
                {
                    "name": "Мерипорт",
                    "lang": "bg"
                },
                {
                    "name": "http://en.wikipedia.org/wiki/Maryport",
                    "lang": "link"
                }
            ],
            "countryName": "United Kingdom",
            "adminCode1": "ENG",
            "lng": "-3.49509",
            "adminName2": "Cumbria",
            "fcodeName": "populated place",
            "adminName3": "Allerdale District",
            "distance": "19.30691",
            "timezone": {
                "dstOffset": 1,
                "gmtOffset": 0,
                "timeZoneId": "Europe/London"
            },
            "adminName4": "",
            "adminName5": "",
            "name": "Maryport",
            "fcode": "PPL",
            "geonameId": 2642927,
            "lat": "54.71434",
            "population": 9854,
            "adminName1": "England",
            "adminId1": "6269131",
            "countryId": "2635167",
            "fclName": "city, village,...",
            "elevation": 0,
            "countryCode": "GB",
            "adminId3": "7290662",
            "adminId2": "2651712",
            "toponymName": "Maryport",
            "fcl": "P",
            "continentCode": "EU"
        },
        {
            "adminCode3": "16UB",
            "adminCode2": "C9",
            "alternateNames": [
                {
                    "name": "http://en.wikipedia.org/wiki/Wigton",
                    "lang": "link"
                }
            ],
            "countryName": "United Kingdom",
            "adminCode1": "ENG",
            "lng": "-3.16114",
            "adminName2": "Cumbria",
            "fcodeName": "populated place",
            "adminName3": "Allerdale District",
            "distance": "41.18233",
            "timezone": {
                "dstOffset": 1,
                "gmtOffset": 0,
                "timeZoneId": "Europe/London"
            },
            "adminName4": "",
            "adminName5": "",
            "name": "Wigton",
            "fcode": "PPL",
            "geonameId": 2633933,
            "lat": "54.82482",
            "population": 5479,
            "adminName1": "England",
            "adminId1": "6269131",
            "countryId": "2635167",
            "fclName": "city, village,...",
            "elevation": 0,
            "countryCode": "GB",
            "adminId3": "7290662",
            "adminId2": "2651712",
            "toponymName": "Wigton",
            "fcl": "P",
            "continentCode": "EU"
        },
        {
            "adminCode3": "16UE",
            "adminCode2": "C9",
            "alternateNames": [
                {
                    "name": "http://en.wikipedia.org/wiki/Millom",
                    "lang": "link"
                }
            ],
            "countryName": "United Kingdom",
            "adminCode1": "ENG",
            "lng": "-3.272",
            "adminName2": "Cumbria",
            "fcodeName": "populated place",
            "adminName3": "Copeland District",
            "distance": "42.91049",
            "timezone": {
                "dstOffset": 1,
                "gmtOffset": 0,
                "timeZoneId": "Europe/London"
            },
            "adminName4": "",
            "adminName5": "",
            "name": "Millom",
            "fcode": "PPL",
            "geonameId": 2642505,
            "lat": "54.21072",
            "population": 6239,
            "adminName1": "England",
            "adminId1": "6269131",
            "countryId": "2635167",
            "fclName": "city, village,...",
            "elevation": 0,
            "countryCode": "GB",
            "adminId3": "7290665",
            "adminId2": "2651712",
            "toponymName": "Millom",
            "fcl": "P",
            "continentCode": "EU"
        }
    ]

}
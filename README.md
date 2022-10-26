# Purpose

Crete scheduled spreadsheet reports as *.csv or *.xlsx files.
You can create custom reports by using the template files and Konfiguration files.




## Konfiguration

![FileFlow](./doc/FileFlow.png)

With the configuration you can define every requested settings in order to set up the reports, the eliona connections and the schedules.

### eliona instance

```JSON
 "eliona_handler": {
    "host": "YOUR_INSTANCE_NAME.eliona.io",
    "api": "https://YOUR_INSTANCE_NAME.eliona.io/api/v2",
    "project_id": 1,
    "api_key": "YOUR_ELIONA_API_KEY"
}
```


|***Configuration***|***Description***|***Example***|
|---|---|---|
|host|Address of the eliona instance without the https|demo.eliona.cloud  
|api|Address of the used api endpoint in this case every time with the https at front |https://develop.eliona.cloud/api/v2|
|project_id|Project number at the used eliona instance. (You can get the number by editing the project and get tne number from the address bar)|1 ![ProjectNumber](./doc/ProjectNumber.png)|
|api_key|The API-Key for the desired eliona instance in order to communicate with the eliona instance|You can get the Key from the eliona engineering Team|  


### Reports  



```JSON

"reports": [
    {
        "name": "Report Name 001",
        "schedule": "monthly",
        "type": "DataListParallel",
        "templateFile": "./tmp_reports/report_001.xlsx",
        "sheet": "Sheet1",
        "fileType": "xlsx",
        "separator":"",
        "firstRow": "0",
        "fromTemplate": true,
        "reportPath": "./tmp_reports/send/report_001.xlsx",
        "receiver": [
            {
                "name": "FirstName LastName",
                "msgType": "email",
                "msgEndpoint": "firstName.LastName@company.ch"
            }                
        ]
    },
    {
        "name": "Report Name 002",
        "schedule": "yearly",
        "type": "DataEntry",
        "templateFile": "./tmp_reports/report_002.csv",
        "sheet": "",
        "fileType": "csv",
        "separator":"\t",
        "firstRow": "0",
        "fromTemplate": true,
        "reportPath": "./tmp_reports/send/report_002.csv",
        "receiver": [
            {
                "name": "FirstName LastName",
                "msgType": "email",
                "msgEndpoint": "firstName.LastName@company.ch"
            }                
        ]
    }
]
```



|***Configuration***|***Description***|***Example***|
|---|---|---|
|name|Set the name of the report. Will be used in logs and the message as reference|Report solar energy building 001 yearly|
|schedule|Set the schedule of the report. Yan be yearly or monthly. Will sent only once at the first day after 6 o'clock.|yearly / monthly|
|type |Define the reporting style|"DataListSequential" = (List underneath)<br> "DataListParallel" = (List parallel)<br>  "DataEntry" = (Single entry in a cell)|
|templateFile|Set the template file path|./templates/syn\_001.xlsx|
|sheet|Sheet name only used if excel file type is used |Tabelle1, Sheet1|
|fileType|Set the required data type|csv, xls, xlsx|
|separator|Separator for csv used spreadsheets only|";" // "," // " "|  
|firstRow|Define the first row to read data from. Default should be 0. The first row will always be ignored as an header|0|  
|fromTemplate|Defines if the report template file will be copied and the data will be set to the cells. Should only be used with excel files. If true every formatting will be kept from the template.|true / false|
|reportPath|Path of the generated report file. Should always be at "./tmp_reports/send"|./tmp_reports/send/report_001.xlsx |
|receiver|List of users to receive the report||           
|name|Sets the name of the receiver. Will be used in the message for text.|FirstName LastName|
|msgType|Selected message type. Currently only eMail is available|email|
|msgEndpoint|Message destination. For type email musst be a valid email address|firstName.LastName@company.ch|
             
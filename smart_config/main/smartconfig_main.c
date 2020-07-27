#include <string.h>
#include <stdlib.h>
#include <stdio.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"

#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_system.h"
#include "esp_smartconfig.h"

#include "nvs_flash.h"
#include "tcpip_adapter.h"
#include "smartconfig_ack.h"

#define SMARTCONFIG_NS      "smartconfig"
#define WIFI_RESTART_NUM    10

static TaskHandle_t smartconfig_handle = NULL;
static EventGroupHandle_t wifi_event_group;
static nvs_handle nvs;

static const int CONNECTED_BIT = ( 1 << 0 );
static const int DISCONNECTED_BIT = ( 1 << 1 );
static const int ESPTOUCH_DONE_BIT = ( 1 << 2 );

static int s_retry_num = WIFI_RESTART_NUM;
static const char *TAG = "sc";

static void smartconfig_task(void * parm);

static void on_wifi_start(void *arg, esp_event_base_t event_base,
                          int32_t event_id, void *event_data)
{
    ESP_ERROR_CHECK(esp_wifi_connect());
    printf("connecting to wifi...\n");
}

static void on_wifi_disconnect(void *arg, esp_event_base_t event_base,
                               int32_t event_id, void *event_data)
{
    system_event_sta_disconnected_t *event = (system_event_sta_disconnected_t *) event_data;

    ESP_LOGI(TAG, "Wi-Fi disconnected, trying to reconnect...");
    
    if (event->reason == WIFI_REASON_BASIC_RATE_NOT_SUPPORT) 
        esp_wifi_set_protocol(ESP_IF_WIFI_STA, WIFI_PROTOCOL_11B 
                                | WIFI_PROTOCOL_11G | WIFI_PROTOCOL_11N);

    if(s_retry_num == 0){
        ESP_LOGI(TAG, "WiFi provisioning timeout, falling back to smartconfig...");

        if(!smartconfig_handle){
            xTaskCreate(smartconfig_task, "smartconfig_task", 4096, 
                            NULL, 3, &smartconfig_handle);
        } else
            xEventGroupSetBits(wifi_event_group, DISCONNECTED_BIT);

        s_retry_num = WIFI_RESTART_NUM;
    } 
    else {
        s_retry_num--;
        ESP_ERROR_CHECK(esp_wifi_connect());
    }
}

static void on_got_ip(void *arg, esp_event_base_t event_base,
                      int32_t event_id, void *event_data)
{
    if(smartconfig_handle)
        xEventGroupSetBits(wifi_event_group, CONNECTED_BIT);
}

static void initialise_wifi(void)
{
    wifi_event_group = xEventGroupCreate();
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    
    wifi_config_t wifi_config;    
    size_t ssid_size, password_size;

    nvs_get_str(nvs, "ssid", NULL, &ssid_size);
    nvs_get_str(nvs, "password", NULL, &password_size);

    char* ssid = malloc(ssid_size);
    char* password = malloc(password_size);

    /*
    *   No credentials in flash memory -> smartconfig
    *   If they are try to connect -> wifi_connect()
    *   
    *   WIFI_EVENT_STA_DISCONNECT s_retry_num times -> drop wifi_connect(), start smartconfig
    */

    if(!nvs_get_str(nvs, "ssid", ssid, &ssid_size) 
        && !nvs_get_str(nvs, "password", password, &password_size)){
        //memcpy(wifi_config.sta.ssid, ssid, ssid_size);
        //memcpy(wifi_config.sta.password, password, password_size);

        memcpy(wifi_config.sta.ssid, "marian", 6);
        memcpy(wifi_config.sta.password, "marianna", 8);

        printf("SSID fetched from flash memory: %s\n", wifi_config.sta.ssid);
        printf("PASSWORD fetched from flash memory: %s\n", wifi_config.sta.password);
    }
    
    /*
    * dont wait for wifi_connect() with empty credentials, go to smartconfig
    */

    else
        s_retry_num = 0;

    tcpip_adapter_init();
    ESP_ERROR_CHECK(esp_event_loop_create_default());

    ESP_ERROR_CHECK(esp_wifi_init(&cfg));

    ESP_ERROR_CHECK(esp_event_handler_register(WIFI_EVENT, WIFI_EVENT_STA_START, &on_wifi_start, NULL));
    ESP_ERROR_CHECK(esp_event_handler_register(WIFI_EVENT, WIFI_EVENT_STA_DISCONNECTED, &on_wifi_disconnect, NULL));
    ESP_ERROR_CHECK(esp_event_handler_register(IP_EVENT, IP_EVENT_STA_GOT_IP, &on_got_ip, NULL));

    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_set_config(ESP_IF_WIFI_STA, &wifi_config))

    ESP_ERROR_CHECK(esp_wifi_start());
}

static void sc_callback(smartconfig_status_t status, void *pdata)
{
    switch (status) {
        case SC_STATUS_WAIT:
            ESP_LOGI(TAG, "smartconfig: wait");
            break;

        case SC_STATUS_FIND_CHANNEL:
            ESP_LOGI(TAG, "smartconfig: waiting for configuration");
            break;

        case SC_STATUS_GETTING_SSID_PSWD:
            ESP_LOGI(TAG, "smartconfig: decoding ssid and password");
            break;

        case SC_STATUS_LINK: ;
            wifi_config_t *wifi_config = pdata;

            ESP_LOGI(TAG, "SSID:%s", wifi_config->sta.ssid);
            ESP_LOGI(TAG, "PASSWORD:%s", wifi_config->sta.password);

            ESP_ERROR_CHECK(nvs_set_str(nvs, "ssid", (char*) wifi_config->sta.ssid));
            ESP_ERROR_CHECK(nvs_set_str(nvs, "password", (char*) wifi_config->sta.password));

            ESP_ERROR_CHECK(esp_wifi_disconnect());
            ESP_ERROR_CHECK(esp_wifi_set_config(ESP_IF_WIFI_STA, wifi_config));
            ESP_ERROR_CHECK(esp_wifi_connect());
            break;

        case SC_STATUS_LINK_OVER:
            xEventGroupSetBits(wifi_event_group, ESPTOUCH_DONE_BIT);
            break;

        default:
            break;
    }
}

static void smartconfig_task(void * parm)
{
    EventBits_t uxBits;

    start_smartconfig:
        ESP_ERROR_CHECK(esp_smartconfig_stop())
        ESP_ERROR_CHECK(esp_smartconfig_set_type(SC_TYPE_ESPTOUCH_AIRKISS));
        ESP_ERROR_CHECK(esp_smartconfig_start(sc_callback));
        
        xEventGroupClearBits(wifi_event_group, CONNECTED_BIT | DISCONNECTED_BIT | ESPTOUCH_DONE_BIT);

    while (1) {
        uxBits = xEventGroupWaitBits(wifi_event_group, CONNECTED_BIT | DISCONNECTED_BIT | ESPTOUCH_DONE_BIT,
                                        true, false, portMAX_DELAY); 

        if(uxBits & CONNECTED_BIT) {
            ESP_LOGI(TAG, "WiFi connected to access point");
        }

        if(uxBits & ESPTOUCH_DONE_BIT) {
            ESP_LOGI(TAG, "smartconfig: WiFi credentials configured, shutting off...");

            esp_smartconfig_stop();
            vTaskDelete(NULL);
        }

        if(uxBits & DISCONNECTED_BIT){
            printf("restarting smartconfig...\n");
            goto start_smartconfig;
        }
    }
}

void app_main()
{
    ESP_ERROR_CHECK(nvs_flash_init());
    ESP_ERROR_CHECK(nvs_open(SMARTCONFIG_NS, NVS_READWRITE, &nvs));

    initialise_wifi();
}


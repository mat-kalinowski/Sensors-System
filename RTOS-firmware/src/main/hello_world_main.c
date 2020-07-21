#include <stdio.h>
#include <string.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"

#include "esp_system.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "esp_event.h"
#include "esp_wifi.h"
#include "mqtt_client.h"
#include "driver/gpio.h"
#include "esp_wifi.h"

#define sensorGPIO      GPIO_NUM_4

static EventGroupHandle_t s_wifi_event_group;
static TaskHandle_t data_sender = NULL;
static esp_mqtt_client_handle_t client;

static int s_retry_num = 10;
uint32_t volatile counter = 0;

static uint8_t mac_addr;
char mac_string[3];


static void sensor_data_reader(void* arg)
{
    uint32_t *ptr = (uint32_t) arg;
    (*ptr)++;
}

static void mqtt_data_sender(void* arg)
{
    while(true){
        char json_msg[50];

        sprintf(json_msg, "{\"nodeId\": \"%d\", \"counter\": %d}", mac_addr, counter);
        esp_mqtt_client_publish(client, "nodes/status", json_msg, 0, 1, 0);

        vTaskDelay(100);
    }
}

#define ESP_WIFI_SSID      CONFIG_ESP_WIFI_SSID
#define ESP_WIFI_PASS      CONFIG_ESP_WIFI_PASSWORD
#define ESP_MAXIMUM_RETRY  CONFIG_ESP_MAXIMUM_RETRY

#define WIFI_CONNECTED_BIT BIT0
#define WIFI_FAIL_BIT      BIT1

static esp_err_t mqtt_event_handler(esp_mqtt_event_handle_t event)
{
    esp_mqtt_client_handle_t client = event->client;

    char start_topic[50];
    char end_topic[50];

    sprintf(start_topic, "tasks/start/%d", mac_addr);
    sprintf(end_topic, "tasks/end/%d", mac_addr);

    switch(event->event_id){
        case MQTT_EVENT_CONNECTED:
            esp_mqtt_client_subscribe(client, "nodes/discover", 0);
            esp_mqtt_client_subscribe(client, start_topic, 0);
            esp_mqtt_client_subscribe(client, end_topic, 0);

            esp_mqtt_client_publish(client, "nodes/discover/response", mac_string, 0, 1, 0);
            ESP_LOGI(mac_string, "Node connected to MQTT broker");
            break;

        case MQTT_EVENT_DISCONNECTED:
            ESP_LOGI(mac_string, "Node disconnected with MQTT broker");
            break;

        case MQTT_EVENT_DATA:
            if(!strncmp("nodes/discover", event->topic, event->topic_len))
                esp_mqtt_client_publish(client, "nodes/discover/response", mac_string, 0, 1, 0);

            else if(!strncmp(start_topic, event->topic, event->topic_len)){
                gpio_isr_handler_add(sensorGPIO, sensor_data_reader, (void *) &counter);
                xTaskCreate(mqtt_data_sender, "mqtt-sender", 4*configMINIMAL_STACK_SIZE,
                             (void*) 0, tskIDLE_PRIORITY, &data_sender);
            }

            else if(!strncmp(end_topic, event->topic, event->topic_len)){
                if(data_sender)
                    vTaskDelete(data_sender);
            }
            break;

        case MQTT_EVENT_ERROR:
            ESP_LOGI(mac_string, "Node MQTT connection error");
            break;

        default:
            break;
    }

    return ESP_OK;
}

void mqtt_setup()
{
    const esp_mqtt_client_config_t mqtt_cfg = {
        .uri = "mqtt://user:user@192.168.1.157",
        .event_handle = mqtt_event_handler,
    };

    client = esp_mqtt_client_init(&mqtt_cfg);
    esp_mqtt_client_start(client);
}

static void wifi_event_handler(void* arg, esp_event_base_t event_base,
                                int32_t event_id, void* event_data)
{
    if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_START) 
    {
        esp_wifi_connect();
        
    } 
    else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_DISCONNECTED) 
    {
        if (s_retry_num < ESP_MAXIMUM_RETRY) 
        {
            esp_wifi_connect();
            s_retry_num++;

            ESP_LOGI(mac_string, "retry to connect to the AP");
        } 
        else 
        {
            xEventGroupSetBits(s_wifi_event_group, WIFI_FAIL_BIT);
        }

        ESP_LOGI(mac_string,"connect to the AP fail");
    } 
    else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP) 
    {
        ip_event_got_ip_t* event = (ip_event_got_ip_t*) event_data;

        ESP_LOGI(mac_string, "got ip:%s",
                 ip4addr_ntoa(&event->ip_info.ip));

        xEventGroupSetBits(s_wifi_event_group, WIFI_CONNECTED_BIT);
        s_retry_num = 0;
    }
}

void wifi_setup()
{
    s_wifi_event_group = xEventGroupCreate();

    tcpip_adapter_init();

    ESP_ERROR_CHECK(esp_event_loop_create_default());

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));

    ESP_ERROR_CHECK(esp_event_handler_register(WIFI_EVENT, ESP_EVENT_ANY_ID, &wifi_event_handler, NULL));
    ESP_ERROR_CHECK(esp_event_handler_register(IP_EVENT, IP_EVENT_STA_GOT_IP, &wifi_event_handler, NULL));

    wifi_config_t wifi_config = {
        .sta = {
            .ssid = ESP_WIFI_SSID,
            .password = ESP_WIFI_PASS
        },
    };

    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA) );
    ESP_ERROR_CHECK(esp_wifi_set_config(ESP_IF_WIFI_STA, &wifi_config) );
    ESP_ERROR_CHECK(esp_wifi_start() );

    EventBits_t bits = xEventGroupWaitBits(s_wifi_event_group,
            WIFI_CONNECTED_BIT | WIFI_FAIL_BIT,
            pdFALSE,
            pdFALSE,
            portMAX_DELAY);

    ESP_ERROR_CHECK(esp_event_handler_unregister(IP_EVENT, IP_EVENT_STA_GOT_IP, &wifi_event_handler));
    ESP_ERROR_CHECK(esp_event_handler_unregister(WIFI_EVENT, ESP_EVENT_ANY_ID, &wifi_event_handler));
    vEventGroupDelete(s_wifi_event_group);
}

void app_main()
{
    gpio_config_t gpio_cfg;

    gpio_cfg.pin_bit_mask = GPIO_Pin_4;
    gpio_cfg.mode = GPIO_MODE_INPUT;
    gpio_cfg.intr_type = GPIO_INTR_POSEDGE;
    gpio_cfg.pull_down_en = 0;
    gpio_cfg.pull_up_en = 0;

    ESP_ERROR_CHECK(esp_efuse_mac_get_default(&mac_addr));
    ESP_ERROR_CHECK(gpio_config(&gpio_cfg));

    sprintf(mac_string, "%d", mac_addr);

    wifi_setup();
    mqtt_setup();

    ESP_ERROR_CHECK(gpio_install_isr_service(0));

    return;
}

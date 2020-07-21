#include <stdio.h>
#include <string.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"

#include "esp_system.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "esp_event.h"
#include "driver/gpio.h"
#include "esp_wifi.h"
#include "mqtt_client.h"

#define sensorGPIO      GPIO_NUM_4

static TaskHandle_t data_sender = NULL;
static esp_mqtt_client_handle_t client;

uint32_t volatile counter = 0;
static uint8_t mac_addr;

char mac_string[3];

void wifi_setup(void);
esp_mqtt_client_handle_t mqtt_setup(mqtt_event_callback_t ev_handler);

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
    client = mqtt_setup(mqtt_event_handler);

    ESP_ERROR_CHECK(gpio_install_isr_service(0));

    return;
}

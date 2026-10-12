<?php
/**
 * Plugin Name:       Visual Search for WooCommerce
 * Description:       "Search by photo" and "similar items" for any WooCommerce store, powered by a FashionCLIP + FAISS visual search API.
 * Version:           2.0.0
 * Requires at least: 6.0
 * Requires PHP:      7.4
 * Author:            Mahmoud Shaker
 * Author URI:        https://github.com/ANaSHaker
 * License:           MIT
 * Text Domain:       visual-search-for-woocommerce
 * Domain Path:       /languages
 * WC requires at least: 7.0
 *
 * @package VisualSearchForWooCommerce
 */

defined( 'ABSPATH' ) || exit;

define( 'VSW_VERSION', '2.0.0' );
define( 'VSW_FILE', __FILE__ );
define( 'VSW_DIR', plugin_dir_path( __FILE__ ) );
define( 'VSW_URL', plugin_dir_url( __FILE__ ) );

require_once VSW_DIR . 'includes/class-vsw-settings.php';
require_once VSW_DIR . 'includes/class-vsw-api-client.php';
require_once VSW_DIR . 'includes/class-vsw-upload-store.php';
require_once VSW_DIR . 'includes/class-vsw-product-presenter.php';
require_once VSW_DIR . 'includes/class-vsw-rest-controller.php';
require_once VSW_DIR . 'includes/class-vsw-indexer.php';
require_once VSW_DIR . 'includes/class-vsw-shortcodes.php';
require_once VSW_DIR . 'includes/class-vsw-plugin.php';

register_activation_hook( __FILE__, array( 'VSW_Plugin', 'activate' ) );
register_deactivation_hook( __FILE__, array( 'VSW_Plugin', 'deactivate' ) );

add_action( 'plugins_loaded', array( 'VSW_Plugin', 'instance' ) );

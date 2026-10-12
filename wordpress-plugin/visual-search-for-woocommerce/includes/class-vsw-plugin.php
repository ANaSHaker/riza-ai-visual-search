<?php
/**
 * Bootstrap: wires every component to WordPress hooks.
 *
 * @package VisualSearchForWooCommerce
 */

defined( 'ABSPATH' ) || exit;

final class VSW_Plugin {

	/** @var VSW_Plugin|null */
	private static $instance = null;

	/** @var VSW_Settings */
	public $settings;

	/** @var VSW_Api_Client */
	public $api;

	/** @var VSW_Upload_Store */
	public $uploads;

	public static function instance() {
		if ( null === self::$instance ) {
			self::$instance = new self();
		}
		return self::$instance;
	}

	private function __construct() {
		load_plugin_textdomain( 'visual-search-for-woocommerce', false, dirname( plugin_basename( VSW_FILE ) ) . '/languages' );

		if ( ! class_exists( 'WooCommerce' ) ) {
			add_action( 'admin_notices', array( $this, 'missing_woocommerce_notice' ) );
			return;
		}

		$this->settings = new VSW_Settings();
		$this->api      = new VSW_Api_Client( $this->settings );
		$this->uploads  = new VSW_Upload_Store();
		$presenter      = new VSW_Product_Presenter();

		$this->settings->register();
		( new VSW_Rest_Controller( $this->settings, $this->api, $this->uploads, $presenter ) )->register();
		( new VSW_Indexer( $this->settings, $this->api ) )->register();
		( new VSW_Shortcodes( $this->settings, $this->api, $presenter ) )->register();

		add_action( 'vsw_cleanup_uploads', array( $this->uploads, 'cleanup' ) );
		add_action( 'wp_enqueue_scripts', array( $this, 'register_assets' ) );
	}

	public function register_assets() {
		wp_register_style( 'vsw-frontend', VSW_URL . 'assets/css/visual-search.css', array(), VSW_VERSION );
		wp_register_script( 'vsw-frontend', VSW_URL . 'assets/js/visual-search.js', array(), VSW_VERSION, true );
		wp_localize_script(
			'vsw-frontend',
			'vswConfig',
			array(
				'restUrl'  => esc_url_raw( rest_url( VSW_Rest_Controller::NAMESPACE ) ),
				'nonce'    => wp_create_nonce( 'wp_rest' ),
				'maxBytes' => VSW_Upload_Store::MAX_BYTES,
				'i18n'     => array(
					'analyzing' => __( 'Finding items in your photo…', 'visual-search-for-woocommerce' ),
					'searching' => __( 'Searching similar products…', 'visual-search-for-woocommerce' ),
					'noResults' => __( 'No similar products found. Try another photo or item.', 'visual-search-for-woocommerce' ),
					'error'     => __( 'Something went wrong. Please try again.', 'visual-search-for-woocommerce' ),
					'tooLarge'  => __( 'The image is too large (max 10 MB).', 'visual-search-for-woocommerce' ),
					'badType'   => __( 'Please choose a JPG, PNG or WebP image.', 'visual-search-for-woocommerce' ),
				),
			)
		);
	}

	public function missing_woocommerce_notice() {
		echo '<div class="notice notice-error"><p>' . esc_html__( 'Visual Search for WooCommerce requires WooCommerce to be active.', 'visual-search-for-woocommerce' ) . '</p></div>';
	}

	public static function activate() {
		if ( ! wp_next_scheduled( 'vsw_cleanup_uploads' ) ) {
			wp_schedule_event( time() + HOUR_IN_SECONDS, 'hourly', 'vsw_cleanup_uploads' );
		}
		VSW_Upload_Store::ensure_dir();
	}

	public static function deactivate() {
		wp_clear_scheduled_hook( 'vsw_cleanup_uploads' );
	}
}

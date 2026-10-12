<?php
/**
 * Settings page (WordPress Settings API). Stores one option array: vsw_settings.
 *
 * @package VisualSearchForWooCommerce
 */

defined( 'ABSPATH' ) || exit;

class VSW_Settings {

	const OPTION = 'vsw_settings';
	const PAGE   = 'vsw-settings';
	const CAP    = 'manage_woocommerce';

	/**
	 * Defaults. min_score 0.30 is the storefront cut-off used in production:
	 * the API threshold (0.20) keeps recall high, the store hides weak matches.
	 */
	public static function defaults() {
		return array(
			'api_url'            => 'http://127.0.0.1:8000',
			'api_key'            => '',
			'top_k'              => 12,
			'min_score'          => 0.30,
			'similar_on_product' => 0,
			'similar_count'      => 8,
			'search_form_button' => 1,
			'auto_index'         => 1,
			'rate_limit'         => 30,
		);
	}

	public function get( $key ) {
		$opts = wp_parse_args( get_option( self::OPTION, array() ), self::defaults() );
		return isset( $opts[ $key ] ) ? $opts[ $key ] : null;
	}

	public function register() {
		add_action( 'admin_menu', array( $this, 'add_page' ) );
		add_action( 'admin_init', array( $this, 'register_settings' ) );
	}

	public function add_page() {
		add_submenu_page(
			'woocommerce',
			__( 'Visual Search', 'visual-search-for-woocommerce' ),
			__( 'Visual Search', 'visual-search-for-woocommerce' ),
			self::CAP,
			self::PAGE,
			array( $this, 'render_page' )
		);
	}

	public function register_settings() {
		register_setting(
			self::PAGE,
			self::OPTION,
			array(
				'type'              => 'array',
				'sanitize_callback' => array( $this, 'sanitize' ),
				'default'           => self::defaults(),
			)
		);

		add_settings_section( 'vsw_api', __( 'API connection', 'visual-search-for-woocommerce' ), '__return_false', self::PAGE );
		add_settings_section( 'vsw_store', __( 'Storefront', 'visual-search-for-woocommerce' ), '__return_false', self::PAGE );

		$fields = array(
			array( 'api_url', __( 'API URL', 'visual-search-for-woocommerce' ), 'vsw_api', 'url' ),
			array( 'api_key', __( 'API key', 'visual-search-for-woocommerce' ), 'vsw_api', 'secret' ),
			array( 'auto_index', __( 'Index products automatically on save', 'visual-search-for-woocommerce' ), 'vsw_api', 'checkbox' ),
			array( 'top_k', __( 'Results per search', 'visual-search-for-woocommerce' ), 'vsw_store', 'number' ),
			array( 'min_score', __( 'Minimum similarity (0–1)', 'visual-search-for-woocommerce' ), 'vsw_store', 'decimal' ),
			array( 'search_form_button', __( 'Add camera button to the product search form', 'visual-search-for-woocommerce' ), 'vsw_store', 'checkbox' ),
			array( 'similar_on_product', __( 'Show "similar items" on product pages', 'visual-search-for-woocommerce' ), 'vsw_store', 'checkbox' ),
			array( 'similar_count', __( 'Similar items to show', 'visual-search-for-woocommerce' ), 'vsw_store', 'number' ),
			array( 'rate_limit', __( 'Searches per visitor per 5 minutes', 'visual-search-for-woocommerce' ), 'vsw_store', 'number' ),
		);
		foreach ( $fields as $f ) {
			add_settings_field(
				'vsw_' . $f[0],
				$f[1],
				array( $this, 'render_field' ),
				self::PAGE,
				$f[2],
				array(
					'key'       => $f[0],
					'type'      => $f[3],
					'label_for' => 'vsw_' . $f[0],
				)
			);
		}
	}

	/**
	 * Sanitize and clamp every value. The API key is write-only: an empty
	 * submission keeps the stored key so it never has to be echoed into HTML.
	 *
	 * @param array $input Raw input.
	 * @return array
	 */
	public function sanitize( $input ) {
		$input = is_array( $input ) ? $input : array();
		$old   = wp_parse_args( get_option( self::OPTION, array() ), self::defaults() );
		$out   = self::defaults();

		$url            = isset( $input['api_url'] ) ? esc_url_raw( trim( $input['api_url'] ), array( 'http', 'https' ) ) : '';
		$out['api_url'] = $url ? untrailingslashit( $url ) : $old['api_url'];

		$key            = isset( $input['api_key'] ) ? sanitize_text_field( $input['api_key'] ) : '';
		$out['api_key'] = '' !== $key ? $key : $old['api_key'];
		if ( ! empty( $input['api_key_clear'] ) ) {
			$out['api_key'] = '';
		}

		$out['top_k']         = min( 48, max( 1, absint( $input['top_k'] ?? 12 ) ) );
		$out['similar_count'] = min( 24, max( 1, absint( $input['similar_count'] ?? 8 ) ) );
		$out['rate_limit']    = min( 500, max( 1, absint( $input['rate_limit'] ?? 30 ) ) );
		$out['min_score']     = min( 1.0, max( 0.0, (float) ( $input['min_score'] ?? 0.30 ) ) );

		foreach ( array( 'similar_on_product', 'search_form_button', 'auto_index' ) as $flag ) {
			$out[ $flag ] = empty( $input[ $flag ] ) ? 0 : 1;
		}
		return $out;
	}

	/**
	 * @param array $args Field args.
	 */
	public function render_field( $args ) {
		$key   = $args['key'];
		$name  = self::OPTION . '[' . $key . ']';
		$id    = 'vsw_' . $key;
		$value = $this->get( $key );

		switch ( $args['type'] ) {
			case 'checkbox':
				printf( '<input type="checkbox" id="%1$s" name="%2$s" value="1" %3$s>', esc_attr( $id ), esc_attr( $name ), checked( 1, (int) $value, false ) );
				break;
			case 'secret':
				printf(
					'<input type="password" id="%1$s" name="%2$s" value="" class="regular-text" autocomplete="new-password" placeholder="%3$s">',
					esc_attr( $id ),
					esc_attr( $name ),
					esc_attr( $value ? __( 'Saved — leave empty to keep', 'visual-search-for-woocommerce' ) : '' )
				);
				if ( $value ) {
					printf(
						' <label><input type="checkbox" name="%s" value="1"> %s</label>',
						esc_attr( self::OPTION . '[api_key_clear]' ),
						esc_html__( 'Remove saved key', 'visual-search-for-woocommerce' )
					);
				}
				echo '<p class="description">' . esc_html__( 'Sent as the X-API-Key header. Must match VS_API_KEY on the API server.', 'visual-search-for-woocommerce' ) . '</p>';
				break;
			case 'url':
				printf( '<input type="url" id="%1$s" name="%2$s" value="%3$s" class="regular-text">', esc_attr( $id ), esc_attr( $name ), esc_attr( $value ) );
				echo '<p class="description">' . esc_html__( 'Keep the API on a private network or localhost; only this server needs to reach it.', 'visual-search-for-woocommerce' ) . '</p>';
				break;
			case 'decimal':
				printf( '<input type="number" step="0.01" min="0" max="1" id="%1$s" name="%2$s" value="%3$s" class="small-text">', esc_attr( $id ), esc_attr( $name ), esc_attr( $value ) );
				break;
			default:
				printf( '<input type="number" min="1" id="%1$s" name="%2$s" value="%3$s" class="small-text">', esc_attr( $id ), esc_attr( $name ), esc_attr( $value ) );
		}
	}

	public function render_page() {
		if ( ! current_user_can( self::CAP ) ) {
			wp_die( esc_html__( 'You do not have permission to access this page.', 'visual-search-for-woocommerce' ) );
		}
		$health = VSW_Plugin::instance()->api->health();
		?>
		<div class="wrap vsw-admin">
			<h1><?php esc_html_e( 'Visual Search', 'visual-search-for-woocommerce' ); ?></h1>

			<div class="notice <?php echo is_wp_error( $health ) ? 'notice-error' : 'notice-success'; ?> inline">
				<p>
				<?php
				if ( is_wp_error( $health ) ) {
					esc_html_e( 'The visual search API is not reachable. Check the API URL and key.', 'visual-search-for-woocommerce' );
				} else {
					/* translators: %s: number of indexed image vectors */
					printf( esc_html__( 'API connected — %s image vectors indexed.', 'visual-search-for-woocommerce' ), esc_html( number_format_i18n( (int) ( $health['vectors'] ?? 0 ) ) ) );
				}
				?>
				</p>
			</div>

			<form action="options.php" method="post">
				<?php
				settings_fields( self::PAGE );
				do_settings_sections( self::PAGE );
				submit_button();
				?>
			</form>

			<h2><?php esc_html_e( 'Index catalogue', 'visual-search-for-woocommerce' ); ?></h2>
			<p><?php esc_html_e( 'Sends every published product image to the API in small batches. Safe to re-run.', 'visual-search-for-woocommerce' ); ?></p>
			<p>
				<button type="button" class="button button-primary" id="vsw-index-start"><?php esc_html_e( 'Start indexing', 'visual-search-for-woocommerce' ); ?></button>
				<span id="vsw-index-status" aria-live="polite"></span>
			</p>
			<p><?php esc_html_e( 'Shortcodes:', 'visual-search-for-woocommerce' ); ?> <code>[vsw_visual_search]</code> <code>[vsw_similar_products id="123" limit="8"]</code></p>
		</div>
		<?php
		wp_enqueue_script( 'vsw-admin', VSW_URL . 'assets/js/admin.js', array(), VSW_VERSION, true );
		wp_localize_script(
			'vsw-admin',
			'vswAdmin',
			array(
				'ajaxUrl' => admin_url( 'admin-ajax.php' ),
				'nonce'   => wp_create_nonce( VSW_Indexer::NONCE ),
				'i18n'    => array(
					'running' => __( 'Indexing… %d products processed', 'visual-search-for-woocommerce' ),
					'done'    => __( 'Done — %1$d images indexed, %2$d failed.', 'visual-search-for-woocommerce' ),
					'error'   => __( 'Indexing stopped because of an error.', 'visual-search-for-woocommerce' ),
				),
			)
		);
	}
}

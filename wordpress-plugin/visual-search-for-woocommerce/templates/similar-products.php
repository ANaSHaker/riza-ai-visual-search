<?php
/**
 * "Similar items" grid.
 *
 * @var string $title    Section title.
 * @var array  $products Product cards from VSW_Product_Presenter::card().
 * @package VisualSearchForWooCommerce
 */

defined( 'ABSPATH' ) || exit;
?>
<section class="vsw-similar">
	<h2 class="vsw-similar-title"><?php echo esc_html( $title ); ?></h2>
	<ul class="vsw-grid">
		<?php foreach ( $products as $p ) : ?>
			<li class="vsw-card">
				<a href="<?php echo esc_url( $p['url'] ); ?>">
					<img src="<?php echo esc_url( $p['image'] ); ?>" alt="<?php echo esc_attr( $p['name'] ); ?>" loading="lazy">
					<span class="vsw-name"><?php echo esc_html( $p['name'] ); ?></span>
					<span class="vsw-price"><?php echo wp_kses_post( $p['price_html'] ); ?></span>
				</a>
			</li>
		<?php endforeach; ?>
	</ul>
</section>
